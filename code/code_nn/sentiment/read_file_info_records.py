# coding=utf-8

import os
import pandas as pd


def read_file_info_records(ere_dir, entity_info_dir, relation_info_dir, event_info_dir, em_args_dir):
    records = []

    ere_suffix = ".rich.ere.xml"
    ere_suffix_length = len(ere_suffix)
    for parent, dirnames, ere_filenames in os.walk(ere_dir):
        for ere_filename in ere_filenames:  # 输出文件信息
            part_name = ere_filename[:-ere_suffix_length]
            entity_filepath = entity_info_dir + part_name + '.csv'
            relation_filepath = relation_info_dir + part_name + '.csv'
            event_filepath = event_info_dir + part_name + '.csv'
            em_args_filepath = em_args_dir + part_name + '.csv'
            record = {}
            if os.path.exists(entity_filepath) is True:
                record['filename'] = part_name
                entity_info_df = pd.read_csv(entity_filepath)
                record['entity'] = entity_info_df.to_dict(orient='records')
            if os.path.exists(relation_filepath) is True:
                record['filename'] = part_name
                relation_info_df = pd.read_csv(relation_filepath)
                record['relation'] = relation_info_df.to_dict(orient='records')
            if os.path.exists(event_filepath) is True:
                record['filename'] = part_name
                event_info_df = pd.read_csv(event_filepath)
                record['event'] = event_info_df.to_dict(orient='records')
                if os.path.exists(em_args_filepath) is True:
                    em_args_df = pd.read_csv(em_args_filepath)
                    record['em_args'] = em_args_df.to_dict(orient='records')
            if record != {}:
                records.append(record)

    return records