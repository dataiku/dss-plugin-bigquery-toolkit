# file to create the BigQuery query from the parameters

def generate_query(params, dataset):
    output_query = "SELECT\n"
    select_query = []
    for field_to_flatten in params["fields_to_flatten"]:
        if "output" in field_to_flatten:
            select_query.append(get_select_command(field_to_flatten["path"], field_to_flatten["output"]))
        else:
            select_query.append(get_select_command(field_to_flatten["path"]))
    output_query += ",\n".join(select_query) + "\n"

    dataset_params = dataset.get_config()["params"]

    if "catalog" in dataset_params and dataset_params["catalog"].strip():
        if "schema" in dataset_params and dataset_params["schema"].strip():
            output_query += "FROM `" + dataset_params["catalog"] + "`.`" + dataset_params["schema"] + "`.`" + dataset_params["table"] + "` as dku_root\n"
        else:
            raise Exception("BigQuery dataset (aka schema) cannot be empty when BigQuery project (aka catalog) is specified")
    elif "schema" in dataset_params and dataset_params["schema"].strip():
        output_query += "FROM `" + dataset_params["schema"] + "`.`" + dataset_params["table"] + "` as dku_root\n"
    else:
        output_query += "FROM `" + dataset_params["table"] + "` as dku_root\n"

    output_query += "\n".join(compute_unnest_commands(params["fields_to_flatten"])) + "\n"

    return output_query

def get_select_command(path, default_name = ""):
    """
    Return the way to reach the variable under the path for the SELECT part of the SQL query
    :param path: path to reach the variable, will be used to generated a name if default_name is empty
    :param default_name: user defined name
    :return: a string describing the variable
    """

    if "[]" in path:
        # unnested value, we need to retrieve the technical value
        # We use a magic trick here since a[].b[].c will create 2 intermediate value,
        # we just need to retrieve the name of the intermediate value of a[].b[].c
        splitted_path = path.split("[]")
        # add "dku_" key to avoid conflict with user data
        intermediate_value = "dku_" + get_technical_column_name(splitted_path[:-1])

        # if exists add the ".c" part to prefix "a__b_"
        if splitted_path[-1] and splitted_path[-1].strip():
            intermediate_value += splitted_path[-1]

        if default_name and default_name.strip():
            return intermediate_value + " AS " + default_name
        elif not '.' in intermediate_value:
            # the intermediate value will be directly shown to the user, let's prettify it by removing the "dku_".
            return intermediate_value + " AS " + intermediate_value[4:].replace("__", "_")
        else:
            return intermediate_value
    else:
        # simple case, starting at the root, so let's specify it to avoid ambiguous pattern
        if default_name and default_name.strip():
            return "dku_root." + path + " AS " + default_name
        else:
            return "dku_root." + path

def compute_unnest_commands(fields_to_flatten):
    """
    For each field describe in fields_to_flatten, create the associated Flatten SQL query.
    :param fields_to_flatten: a list of object with the fields to unnest
    :return: a list of string describing how ot unnest the variable in SQL format
    """
    flatten_expressions = []
    path_cache = [] # keep track of the computed path to avoid writing them multiple times
    for field_to_flatten in fields_to_flatten:
        if "[]" in field_to_flatten["path"]:
            input_parts = field_to_flatten["path"].split("[]")[:-1]
            prefix = ""
            for input_part in input_parts:
                if prefix: # element that was unnested multiple times
                    # example of the last iteration of the loop from a[].b[].c[]
                    # tech_name will be a__b__c
                    tech_name = prefix + get_technical_column_name([input_part])
                    if tech_name not in path_cache:
                        # current_path will be a__b_.c
                        current_path = prefix + input_part
                        flatten_expressions += [get_unnest_command(current_path, tech_name)]
                        path_cache.append(tech_name)
                else: # element from the root path
                    # add "dku_" key to avoid conflict with user data
                    tech_name = "dku_" + get_technical_column_name([input_part])
                    if tech_name not in path_cache:
                        # first element, we specify that we are on the root to avoid ambiguous path
                        current_path = "dku_root." + input_part
                        flatten_expressions += [get_unnest_command(current_path, tech_name)]
                        path_cache.append(tech_name)
                prefix = tech_name # Remove the last "_" so the prefix can be joined again
    return flatten_expressions

def get_unnest_command(path, name):
    """
    Return the unnest SQL command for a given path
    :param path: path to reach the variable, will be used to generated a name if default_name is empty
    :param name: name of the intermediate variable
    :return: the unnest SQL command as a String
    """
    # As a sidenote the column name can only be letters (a-z, A-Z), numbers (0-9), or underscores (_).
    return "LEFT JOIN UNNEST(" + path + ") AS " + name


def get_technical_column_name(splitted_path):
    """
    Generate an unique technical name associated to the current path
    :param path: path to reach the variable
    :return: a unique technical name
    """
    return "_".join(splitted_path).replace(".", "_") + "_"