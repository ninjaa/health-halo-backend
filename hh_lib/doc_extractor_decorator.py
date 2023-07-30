import functools
import re

functions = []


def doc_extractor(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    doc_lines = func.__doc__.strip().split("\n")
    description = doc_lines[0]

    # Extract details if present
    details_index = None
    for idx, line in enumerate(doc_lines):
        if line.strip() == "Details:":
            details_index = idx
            break

    if details_index is not None:
        description += " " + " ".join([line.strip()
                                      for line in doc_lines[details_index+1:]])

    raises = None
    for line in doc_lines:
        if "Raises:" in line:
            raises = line.split("Raises:")[1].strip()
            break

    arg_list = list(func.__annotations__.keys())
    if 'return' in arg_list:
        arg_list.remove('return')

    args_str = []
    for arg in arg_list:
        arg_description_match = re.search(
            rf"{arg} \({func.__annotations__[arg]}\): (.+)", func.__doc__)
        arg_description = arg_description_match.group(
            1) if arg_description_match else "Description needed."
        args_str.append(
            f"{arg} ({func.__annotations__[arg]}): {arg_description}")

    # Extract return information
    return_info = None
    return_start = None
    for idx, line in enumerate(doc_lines):
        if "Returns:" in line:
            return_start = idx
            break

    if return_start is not None:
        return_lines = []
        for line in doc_lines[return_start+1:]:
            if not line.strip():
                break
            return_lines.append(line.strip())
        return_info = ' '.join(return_lines)

    function_dict = {
        "name": func.__name__,
        "description": description,
        "required_arguments": args_str,
        "returns": f"{func.__annotations__['return']}: {return_info}" if 'return' in func.__annotations__ and return_info else None,
        "raises": raises,
        "example_call": f"{func.__name__}({', '.join([f'{arg}=value' for arg in arg_list])})"
    }

    functions.append(function_dict)

    return wrapper
