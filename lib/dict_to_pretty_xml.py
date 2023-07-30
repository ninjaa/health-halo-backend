from lxml import etree

def dict_to_pretty_xml(function_dicts):
    root = etree.Element("functions")

    for function_dict in function_dicts:
        function = etree.SubElement(root, "function")

        name = etree.SubElement(function, "function_name")
        name.text = function_dict["name"]

        description = etree.SubElement(function, "function_description")
        description.text = function_dict["description"]

        for arg in function_dict["required_arguments"]:
            required_argument = etree.SubElement(function, "required_argument")
            required_argument.text = arg

        returns = etree.SubElement(function, "returns")
        returns.text = function_dict["returns"]

        if function_dict["raises"]:
            raises = etree.SubElement(function, "raises")
            raises.text = function_dict["raises"]

        example_call = etree.SubElement(function, "example_call")
        example_call.text = function_dict["example_call"]

    return etree.tostring(root, pretty_print=True, encoding='utf-8').decode('utf-8')

