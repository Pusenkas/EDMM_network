import os
import argparse
from .network import NetworkParser


def main():
    parser = argparse.ArgumentParser(description='Desc')
    parser.add_argument('-i', '--input_file', required=True, type=str, help='path of input file')
    parser.add_argument('-o', '--output_dir', required=True, type=str, help='path of output directory')
    parser.add_argument('-k', '--keys', required=True, type=str, help='path of file with private keys')
    parser.add_argument('-t', '--test_mode', action='store_true',
                        help='Use default kubernetes template instead of transforming with EDMM')

    args = parser.parse_args()
    input_file, output_dir, keys, test_mode = args.input_file, args.output_dir, args.keys, args.test_mode

    if not (os.path.exists(input_file) and os.path.isfile(input_file)):
        print("input file doesn't exist")
        return

    if not (os.path.exists(output_dir) and os.path.isdir(output_dir)):
        print("output directory doesn't exist")
        return

    parser = NetworkParser(input_file, output_dir, keys, test_mode)
    parser.parse()


if __name__ == '__main__':
    main()
