WireGaurd_interface = '''\
    [Interface]
    Address = {address}/{prefix}
    ListenPort = {listen_port}
    PrivateKey = {private_key}
    PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o ENI -j MASQUERADE
    PostUp = sysctl -w -q net.ipv4.ip_forward=1
    PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o ENI -j MASQUERADE
    PostDown = sysctl -w -q net.ipv4.ip_forward=0
'''

WireGaurd_peer = '''\
    [Peer]
    PublicKey = {public_key}
    AllowedIPs = {allowed_ip}
    Endpoint = {endpoint}
'''

Kubernetes_secret = '''\
---
apiVersion: v1
kind: Secret
metadata:
  name: wireguard
  namespace: example
type: Opaque
stringData:
  wg0.conf.template: |
{wg_config}
'''

Kubernetes_initContainers = '''\
- name: "wireguard-template-replacement"
  image: "busybox"
  command: ["sh", "-c", "ENI=$(ip route get 8.8.8.8 | grep 8.8.8.8 | awk '{print $5}'); sed \\"s/ENI/$ENI/g\\" /etc/wireguard-secret/wg0.conf.template > /etc/wireguard/wg0.conf; chmod 400 /etc/wireguard/wg0.conf"]
  volumeMounts:
    - name: wireguard-config
      mountPath: /etc/wireguard/
    - name: wireguard-secret
      mountPath: /etc/wireguard-secret/
'''

Kubernetes_containers = '''\
- name: "wireguard"
  image: "linuxserver/wireguard:latest"
  ports:
    - containerPort: {container_port}
  env:
    - name: "PEERS"
      value: "example"
  volumeMounts:
    - name: wireguard-config
      mountPath: /etc/wireguard/
      readOnly: true
  securityContext:
    privileged: true
    capabilities:
      add:
        - NET_ADMIN
'''

Kubernetes_volumes = '''\
- name: wireguard-config
  emptyDir: {}
- name: wireguard-secret
  secret:
    secretName: wireguard
'''

Kubernetes_imagePullSecrets = '''\
- name: docker-registry
'''

Kubernetes_service = '''\
---
apiVersion: v1
kind: Service
metadata:
  name: wireguard
spec:
  type: LoadBalancer
  ports:
    - name: wireguard
      port: {port}
      protocol: UDP
      targetPort: {port}
  selector:
    name: wireguard
'''
