import os

def is_valid_teacher(name):
    return isinstance(name, str) and name.count(",") == 1 and all(part.strip() for part in name.split(","))


def get_file(data_dir, extensions):
    
    data_files = [os.path.join(data_dir, filename) for filename in os.listdir(data_dir) if allowed_file(filename, extensions)]

    if not data_files:
        return None  # No file found

    data_file = max(data_files, key=os.path.getmtime)

    return data_file

def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions and not filename.startswith("~$")


def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
