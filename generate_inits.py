import os

def add_init_py(folder_path):
    for root, dirs, files in os.walk(folder_path):
        init_path = os.path.join(root, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write("# Makes this a Python module\n")
            print(f"🧩 Created: {init_path}")

if __name__ == "__main__":
    base_folder = os.path.dirname(os.path.abspath(__file__))
    add_init_py(base_folder)
