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
    tab_files_path = sys.argv[2]
else:
    exit("Please give source database url as the first argument and the path to output folder as second argument")

with open('write_more_csvs.yaml', 'r') as yaml_file:
    csvs_to_write = yaml.safe_load(yaml_file)

with DatabaseMapping(url_db) as source_db:
    maps = FetchedMaps.fetch(source_db)
    query = parameter_value_sq(source_db)
    for csv_name, rules in csvs_to_write.items():
        index_dim_names = rules["index_dim_names"]
        processed_data = []
        for entity_class, spec in rules["entity_classes"].items():
            df_collect = pd.DataFrame()
            if isinstance(spec, list):
                if len(spec) > 2:
                    for param_name in spec[2]:
                        final_query = (
                            source_db.query(query)
                                .filter(query.c.entity_class_name == entity_class)
                                .filter(query.c.parameter_definition_name == param_name)
                                #.filter(query.c.scenario_name == )
                        ).subquery()
                        df = fetch_as_dataframe(source_db, final_query, maps)
                        df = df.drop(columns=["entity_class_name", "alternative_name", "parameter_definition_name"])
                        df.columns.values[-1] = param_name
                        df.set_index(index_dim_names, inplace=True)
                        if df_collect.empty:
                            df_collect = df
                        else:
                            df_collect = df_collect.join(df, how='outer')
                else:
                    entities = source_db.find_entities(entity_class_name=entity_class)
                    entity_list = list_from_objects(entities)
                    df = pd.DataFrame(entity_list)
            else:
                exit(f"Type error for {spec}")

        df_collect.to_csv(f"{csv_name}.csv")


with open('write_csvs.yaml', 'r') as yaml_file:
    csvs_to_write = yaml.safe_load(yaml_file)

with DatabaseMapping(url_db) as source_db:
    maps = FetchedMaps.fetch(source_db)
    query = parameter_value_sq(source_db)
    for csv_name, class__spec_list  in csvs_to_write.items():
        df = pd.DataFrame()
        processed_data = []
        entity_index_name = None
        for class__spec in class__spec_list:
            for entity_class, spec in class__spec.items():
                entities = source_db.find_entities(entity_class_name=entity_class)
                entity_list = list_from_objects(entities)
                entity_class_dimen_names = entity_class.split('__')

                if isinstance(spec, list):
                    output_dimen_names = []
                    for i in spec[0]:
                        output_dimen_names.append(entity_class_dimen_names[i])
                    entity_index_name = '__'.join(output_dimen_names)
                    for param_name in spec[1]:
                        final_query = (
                            source_db.query(query)
                                .filter(query.c.entity_class_name == entity_class)
                                .filter(query.c.parameter_definition_name == param_name)
                                #.filter(query.c.scenario_name == )
                        ).subquery()
                        df_new = fetch_as_dataframe(source_db, final_query, maps)
                        if not df_new.empty:
                            name_lists = []
                            # Need to add _1, _2 etc to the end of index names if there are duplicates
                            unique_names_count = {}
                            for i, output_dimen_name in enumerate(output_dimen_names):
                                if output_dimen_name in unique_names_count:
                                    unique_names_count[output_dimen_name] += 1
                                else:
                                    unique_names_count[output_dimen_name] = 1
                            unique_counter = deepcopy(unique_names_count)
                            for name in unique_names_count:
                                unique_counter[name] = 0
                            for i, output_dimen_name in enumerate(output_dimen_names):
                                if unique_names_count[output_dimen_name] > 1:
                                    unique_counter[output_dimen_name] += 1
                                    output_dimen_name = f"{output_dimen_name}_{unique_counter[output_dimen_name]}"
                                name_lists.append(df_new[output_dimen_name].tolist())
                            if len(spec) > 2:
                                for i in spec[2]:
                                    index_loc = i + len(entity_class_dimen_names) + 3
                                    name_lists.append(df_new.iloc[:, index_loc].tolist())
                            name_list = ['__'.join(items) for items in zip(*name_lists)]
                            query_dict = dict(zip(name_list, df_new["value"]))
                            processed_data.append((param_name, query_dict))
                elif isinstance(spec, dict):
                    for param_name, dimens in spec.items():
                        entity_index_name = '__'.join([entity_class_dimen_names[i] for i in dimens[0]])
                        key_list = []
                        value_list = []
                        for item in entity_list:
                            parts = item.split('__')
                            key_list.append('__'.join(parts[i] for i in dimens[0]))
                            value_list.append('__'.join(parts[i] for i in dimens[1]))
                        entity_dict = dict(zip(key_list, value_list))
                        processed_data.append((param_name, entity_dict))
                else:
                    exit(f"Type error for {spec}")
        all_indices = set()
        for _, data_dict in processed_data:
            all_indices.update(data_dict.keys())
        all_indices = sorted(all_indices)

        result = pd.DataFrame({"index_name_temp4234": all_indices})

        # if len(spec) > 2:
        #     all_indices_list = []
        #     for index in all_indices:
        #         index_split = index.split('__')
        #         for i, index_name in enumerate(index_split):
        #             all_indices_list[i].append(index_name)
        #     for i in spec[0]:
        #         result[param_name] = result["index_name_temp4234"].map(all_indices_list[i])


        for param_name, data_dict in processed_data:
            # Use map with a dictionary for fast value assignment
            result[param_name] = result["index_name_temp4234"].map(data_dict)

        result = result.drop("index_name_temp4234", axis=1)

        result.to_csv(f"{csv_name}.csv", index=False)


