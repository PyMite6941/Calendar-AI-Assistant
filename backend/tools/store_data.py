# Modules for functionality
import argparse
# Modules for style
from rich.console import Console

console = Console()
args = argparse.ArgumentParser()
args.add_argument("--store", metavar='DATA', help="Stores data in the file")
args.add_argument("--path", default="backend/storage/data.txt", help="Path to the data file")
args = args.parse_args()

def store_data(data):
    with open(args.path, "w") as file:
        file.write(data)
    return "Data stored successfully."

if args.store:
    console.print(store_data(args.store))