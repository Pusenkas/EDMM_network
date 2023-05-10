import yaml
import json
from pywgkey import WgKey
import os
import glob
from . import templates


class NetworkParser:
    """Class for transforming edmm model into kubernetes deployment"""
    DEFAULT_LISTEN_PORT = 50102
    DEFAULT_CONTAINER_PORT = 50102

    edmm_config = None
    keys = None

    def __init__(self, input_file, output_dir, keys, test_mode):
        self.keys_file = keys
        self.output_dir = output_dir
        self.test_mode = test_mode
        with open(input_file, "r") as f:
            self.edmm_config = yaml.safe_load(f)
        with open(keys, "r") as f:
            self.keys = json.load(f)

    def mocked_edmm(self, edmm):
        """Transforms using static template"""
        with open("EDMM/k8s_template.yaml", "r") as f:
            content = f.read()
        with open(os.path.join(self.output_dir, "deployment.yaml"), "w") as f:
            f.write(content)

    def real_edmm(self, edmm):
        """Transforms using edmm"""
        import subprocess

        with open(os.path.join(self.output_dir, "edmm.yaml"), "w") as f:
            yaml.safe_dump(edmm, f)
        try:
            subprocess.run(f"edmm transform kubernetes {os.path.join(self.output_dir, 'edmm.yaml')}",
                           capture_output=True)
        except FileNotFoundError:
            print("Unable to find EDMM")
        os.remove(os.path.join(self.output_dir, 'edmm.yaml'))

    def parse(self):
        """Parses edmm file"""
        edmm_without_network = {key: val for key, val in self.edmm_config.items() if key != "network"}
        if self.test_mode:
            self.mocked_edmm(edmm_without_network)
        else:
            self.real_edmm(edmm_without_network)
        if (network_setting := self.edmm_config.get("network", None)) is None:
            return

        match network_setting.get("type", None):
            case "VPN":
                self.VPN_setup(network_setting.get("components", None),
                               network_setting.get("Listen_port", NetworkParser.DEFAULT_LISTEN_PORT),
                               network_setting.get("peers", None))
            case None:
                print("Type of network component is not specified")
                return

    def VPN_setup(self, components, listen_port, peers):
        """Creates kubernetes config based on parameters"""
        if components is None:
            print("Address has to be specified")
            return
        if peers is None:
            print("Peers has to be specified")
            return

        for component in components:
            name, address = component["name"], component["Address"]

            for config_file in glob.glob("output/*"):
                found = False
                with open(config_file, "r") as f:
                    k8s_configs = yaml.safe_load_all(f)
                    configs = []
                    for config in k8s_configs:
                        if config.get("kind", None) != "Deployment" or \
                                config.get("metadata", None) is None or config["metadata"].get("name", None) != name:
                            configs.append(config)
                            continue
                        found = True
                        print(config["metadata"].get("name", None), name)
                        init_containers = config["spec"]["template"]["spec"].get("initContainers", [])
                        init_containers += yaml.safe_load(templates.Kubernetes_initContainers)
                        config["spec"]["template"]["spec"]["initContainers"] = init_containers

                        containers = config["spec"]["template"]["spec"].get("containers", [])
                        containers += yaml.safe_load(templates.Kubernetes_containers.format(
                            container_port=NetworkParser.DEFAULT_CONTAINER_PORT))
                        config["spec"]["template"]["spec"]["containers"] = containers

                        volumes = config["spec"]["template"]["spec"].get("volumes", [])
                        volumes += yaml.safe_load(templates.Kubernetes_volumes)
                        config["spec"]["template"]["spec"]["volumes"] = volumes

                        image_pull_secrets = config["spec"]["template"]["spec"].get("imagePullSecrets", [])
                        image_pull_secrets += yaml.safe_load(templates.Kubernetes_imagePullSecrets)
                        config["spec"]["template"]["spec"]["imagePullSecrets"] = image_pull_secrets

                        configs.append(config)
                if found:
                    wg_config = self.wg_config(address, listen_port, peers)
                    secret = yaml.safe_load(templates.Kubernetes_secret.format(wg_config=wg_config))
                    service = yaml.safe_load(templates.Kubernetes_service.format(port=listen_port))
                    configs.extend((secret, service))
                    with open(config_file, "w") as f:
                        yaml.safe_dump_all(configs, f)

    def wg_config(self, address, listen_port, peers):
        """Creates WireGuard config"""
        address, prefix = address.split("/")
        config = ""
        config += templates.WireGaurd_interface.format(address=address, listen_port=listen_port, prefix=prefix,
                                                       private_key=self.get_key(address)["private"])
        for peer in peers:
            allowed_ip, endpoint = peer.get("AllowedIP", None), peer.get("Endpoint", None)
            if allowed_ip is None:
                print("All allowedIPs have to be specified")
                return
            if endpoint is None:
                print("All endpoints have to be specified")
                return
            config += templates.WireGaurd_peer.format(
                public_key=self.get_key(allowed_ip)["public"],
                allowed_ip=allowed_ip, endpoint=endpoint)
        return config

    def get_key(self, address):
        """Returns existing pair of keys for a specific address or generate new pair for this address"""
        if address in self.keys:
            return self.keys[address]
        else:
            pair = WgKey()
            self.keys[address] = {"private": pair.privkey, "public": pair.pubkey}
            with open(self.keys_file, "w") as f:
                json.dump(self.keys, f)
            return self.keys[address]
