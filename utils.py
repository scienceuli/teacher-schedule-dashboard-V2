def is_valid_teacher(name):
    return isinstance(name, str) and name.count(",") == 1 and all(part.strip() for part in name.split(","))