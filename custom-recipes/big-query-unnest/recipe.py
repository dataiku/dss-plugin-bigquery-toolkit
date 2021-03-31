from dataiku.customrecipe import get_recipe_config
from dataiku.core.sql import SQLExecutor2
from recipe_config_loading import get_input_output, parse_recipe_config
from query_generator import generate_query
import logging

# retrieve all the recipe UI parameters (from $scope.config)
recipe_config = get_recipe_config()
logging.info("recipe_config: " + recipe_config)

# retrieve the input and output dataiku.Dataset using their "name" in the recipe.json file
input_dataset, output_dataset = get_input_output()

# parse the UI parameters into a dict
params = parse_recipe_config(recipe_config)

# generate a BigQuery query from the parsed UI parameters and the input_dataset (needed to know the connection type, but we could hardcode 'BigQuery')
query = generate_query(params, input_dataset)

# Push the query on the BigQuery engine and put the results of the execution of the select query into the output_dataset
sql_executor = SQLExecutor2(dataset=input_dataset)
sql_executor.exec_recipe_fragment(output_dataset, query)