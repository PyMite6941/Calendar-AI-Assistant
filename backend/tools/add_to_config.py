# Modules for functionality
import argparse
import tomlkit

parser = argparse.ArgumentParser()
parser.add_argument("--read", action="store_true", help="Reads the config file")
parser.add_argument("--set", nargs=2, metavar=('KEY', 'VALUE'), help="Sets a value in the config file")

def read_toml(path="backend/storage/configs.toml"):
    with open(path,'r') as file:
        return tomlkit.load(file)