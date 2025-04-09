from copy import deepcopy

import spinedb_api as api
from spinedb_api import DatabaseMapping
from spinedb_api.dataframes import to_dataframe
from spinedb_api.dataframes import FetchedMaps
from spinedb_api.dataframes import parameter_value_sq, fetch_as_dataframe
import sys
import yaml
import csv
import pandas as pd
import numpy as np

def list_from_objects(objects):
    object_list = []
    for obj in objects:
        object_list.append(obj["name"])
    return object_list


if len(sys.argv) > 1:
    url_db = sys.argv[1]
else:
    exit("Please give source database url as the first argument and the path to output folder as second argument")
if len(sys.argv) > 2:
    output_files_path = sys.argv[2]
else:
    exit("Please give source database url as the first argument and the path to output folder as second argument")

with open('write_csvs.yaml', 'r') as yaml_file:
    csvs_to_write = yaml.safe_load(yaml_file)

with DatabaseMapping(url_db) as source_db:
    maps = FetchedMaps.fetch(source_db)
    query = parameter_value_sq(source_db)
    for csv_name, rules in csvs_to_write.items():
        target_index_dim_names = rules["index_dim_names"]
        df_collect = pd.DataFrame()

        if bool(rules.get("dims_to_parameters")):
            for entity_class, dim_specs in rules["dims_to_parameters"].items():
                if all(isinstance(item, list) for item in dim_specs):
                    if len(dim_specs) == 1:
                        source_index_dim_names = target_index_dim_names
                        dims_to_parameters = dim_specs[0]
                    elif len(dim_specs) == 2:
                        source_index_dim_names = dim_specs[0]
                        dims_to_parameters = dim_specs[1]
                    else:
                        exit(f"dims_to_parameters specification has wrong number of lists inside lists (has to be one or two): {dim_specs}")
                else:
                    source_index_dim_names = target_index_dim_names
                    dims_to_parameters = dim_specs
                class_dims_in_db = entity_class_from_db[0]["entity_class_byname"]
                entities = source_db.find_entities(entity_class_name=entity_class)
                entity_class_from_db = source_db.find_entity_classes(name=entity_class)
                dims = []
                for spec_dim_name in source_index_dim_names:
                    found_flag = False
                    for j, db_dim_name in enumerate(class_dims_in_db):
                        if spec_dim_name == db_dim_name:
                            dims.append(j)
                            found_flag = True
                            break
                    if not found_flag:
                        exit(f"Couldn't find dimension {spec_dim_name} for {entity_class} spec {dim_specs}")
                dims_p = []
                for dim_to_parameter in dims_to_parameters:
                    found_flag = False
                    for j, db_dim_name in enumerate(class_dims_in_db):
                        if dim_to_parameter == db_dim_name:
                            dims_p.append(j)
                            found_flag = True
                            break
                    if not found_flag:
                        exit(f"Couldn't find dimension {dim_to_parameter} for {entity_class} spec {dim_specs}")
                entity_list = list_from_objects(entities)
                df = pd.DataFrame(columns=target_index_dim_names + dims_to_parameters)
                for i, entity in enumerate(entity_list):
                    df.loc[len(df)] = entity.split('__')
                df.set_index(target_index_dim_names, inplace=True)
                if df_collect.empty:
                    df_collect = df
                else:
                    df_collect = df_collect.join(df, how='outer')

        if bool(rules.get("parameters")):
            for entity_class, param_specs in rules["parameters"].items():
                reorder_indexes = None
                if all(isinstance(item, list) for item in param_specs):
                    if len(param_specs) == 1:
                        source_index_dim_names = target_index_dim_names
                        param_names = param_specs[0]
                    elif len(param_specs) == 2:
                        source_index_dim_names = param_specs[0]
                        param_names = param_specs[1]
                    elif len(param_specs) == 3:
                        reorder_indexes = param_specs[0]
                        source_index_dim_names = param_specs[1]
                        param_names = param_specs[2]
                    else:
                        exit(f"dims_to_parameters specification has wrong number of lists inside lists (has to be one or two): {param_specs}")
                else:
                    source_index_dim_names = target_index_dim_names
                    param_names = param_specs
                for param_name in param_names:
                    param_name_target = deepcopy(param_name)
                    if isinstance(param_name, list):
                        param_name_target = param_name[1]
                        param_name = param_name[0]
                    final_query = (
                        source_db.query(query)
                            .filter(query.c.entity_class_name == entity_class)
                            .filter(query.c.parameter_definition_name == param_name)
                            #.filter(query.c.scenario_name == )
                    ).subquery()
                    df = fetch_as_dataframe(source_db, final_query, maps)
                    if not df.empty:
                        df = df.drop(columns=["entity_class_name", "alternative_name", "parameter_definition_name"])

                        # Rename column/index names to the target (instead of source db that the fetch got)
                        if reorder_indexes:
                            new_column_order = []
                            for i in reorder_indexes:
                                new_column_order.append(source_index_dim_names[i])
                            new_column_order = new_column_order + df.columns.values.tolist()[len(reorder_indexes):]
                            df = df[new_column_order]
                        for i, target_dim_name in enumerate(target_index_dim_names):
                            df.rename(columns={df.columns.values[i]: target_dim_name}, inplace=True)
                        df.rename(columns={df.columns.values[-1]: param_name_target}, inplace=True)
                        df.set_index(target_index_dim_names, inplace=True)
                    else:
                        df = pd.DataFrame(columns=target_index_dim_names + [param_name_target])
                        df.set_index(target_index_dim_names, inplace=True)
                    if df_collect.empty and df_collect.columns.empty:
                        df_collect = df
                    else:
                        df_collect = df_collect.join(df, how='outer')

        df_collect.to_csv(f"{output_files_path}/{csv_name}.csv")

