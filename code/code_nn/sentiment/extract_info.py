# coding=utf-8

import os
import pandas as pd
import xml.dom.minidom
import operator

from constants import *
from split_sentences import *
from find_source import *

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


def extract_entity_each_file(source_filepath, ere_filepath, annotation_filepath, part_name):
    entity_records_each_file = []
    predict_sources = []  # 自己预测的源
    
    source_fp = open(source_filepath)
    all_source_text = source_fp.read().decode("utf-8")  # 注意编码
    sentences = split_sentences(all_source_text)  # 分句

    ere_file = xml.dom.minidom.parse(ere_filepath)
    ere_root = ere_file.documentElement
    entity_list = ere_root.getElementsByTagName('entity')

    annotation_file = xml.dom.minidom.parse(annotation_filepath)
    annotation_root = annotation_file.documentElement
    annotation_sentiment_list = annotation_root.getElementsByTagName('sentiment_annotations')
    annotation_sentiment_list = annotation_sentiment_list[0]
    annotation_entity_list = annotation_sentiment_list.getElementsByTagName('entity')  # 实际上是entity mention

    for i in range(len(entity_list)):
        # entity信息
        entity_id = entity_list[i].getAttribute('id')
        entity_type = entity_list[i].getAttribute('type')
        entity_specificity = entity_list[i].getAttribute('specificity')
        entity_mention_list = entity_list[i].getElementsByTagName('entity_mention')

        for j in range(len(entity_mention_list)):
            entity_mention_id = entity_mention_list[j].getAttribute('id')

            # entity mention信息
            entity_mention_noun_type = entity_mention_list[j].getAttribute('noun_type')
            entity_mention_offset = int(entity_mention_list[j].getAttribute('offset'))
            entity_mention_length = int(entity_mention_list[j].getAttribute('length'))
            text = entity_mention_list[j].getElementsByTagName('mention_text')
            text = text[0]
            text_text = text.firstChild.data
            # 上下文信息
            above = 3
            below = 3
            context_dict = find_context(entity_mention_offset, sentences, text_text, above, below)
            # print context_dict
            if context_dict is None:  # 说明是在标签中出现的源
                entity_mention = {
                    'ere_id': entity_mention_id, 'offset': entity_mention_offset,
                    'length': entity_mention_length, 'text': text_text
                }
                predict_sources.append(entity_mention)
                continue
            # 拼成一个字符串
            context = context_dict_to_string(context_dict, above, below)

            # polarity
            for k in range((len(annotation_entity_list))):
                annotation_entity_id = annotation_entity_list[k].getAttribute('ere_id')
                if annotation_entity_id == entity_mention_id:
                    st_em = annotation_entity_list[k].getElementsByTagName('sentiment')
                    # if len(st_em) == 0:
                    #     logger.info("错误：无情感标签。" + " " + part_name + " " + annotation_relation_id +
                    #                 " " + relation_mention_id)
                    label_polarity = st_em[0].getAttribute('polarity')
                    break
            # if label_polarity == 'none':
            #     break  # 如果为none则丢弃该样本

            # actual source
            source = st_em[0].getElementsByTagName('source')
            if label_polarity == 'none' or len(source) == 0:
                source_id = ''
                source_offset = 0
                source_length = 0
                source_text = ''
                # if len(source) == 0:
                #     print part_name, label_polarity, entity_mention_id
            else:
                source = source[0]
                source_id = source.getAttribute('ere_id')
                source_offset = int(source.getAttribute('offset'))
                source_length = int(source.getAttribute('length'))
                source_text = source.firstChild.data

            entity_record = {
                'entity_id': entity_id, 'entity_type': entity_type, 'entity_specificity': entity_specificity,
                'entity_mention_id': entity_mention_id, 'entity_mention_noun_type': entity_mention_noun_type,
                'entity_mention_offset': entity_mention_offset, 'entity_mention_length': entity_mention_length,
                'entity_mention_text': text_text, 'entity_mention_context': context,
                'file': part_name, 'label_polarity': label_polarity,
                'source_id': source_id, 'source_offset': source_offset, 'source_length': source_length,
                'source_text': source_text
            }

            entity_records_each_file.append(entity_record)

    predict_sources = sorted(predict_sources, key=operator.itemgetter('offset'))  # 按offset升序排序
    for i in range(len(entity_records_each_file)):
        offset = entity_records_each_file[i]['entity_mention_offset']
        predict_source = find_source(offset, predict_sources)
        # print predict_source
        if predict_source is not None:
            entity_records_each_file[i]['predict_source_id'] = predict_source['ere_id']
            entity_records_each_file[i]['predict_source_offset'] = predict_source['offset']
            entity_records_each_file[i]['predict_source_length'] = predict_source['length']
            entity_records_each_file[i]['predict_source_text'] = predict_source['text']
        else:
            entity_records_each_file[i]['predict_source_id'] = ''
            entity_records_each_file[i]['predict_source_offset'] = 0
            entity_records_each_file[i]['predict_source_length'] = 0
            entity_records_each_file[i]['predict_source_text'] = ''

    return entity_records_each_file, predict_sources


# rel_arg的所属entity信息
def rel_arg_entity_info(entity_list, rel_arg_id, rel_arg_mention_id, rel_arg_text, sentences):
    # 根据id找所在entity和mention
    for k in range((len(entity_list))):
        entity_id = entity_list[k].getAttribute('id')
        if rel_arg_id == entity_id:
            rel_arg_entity_type = entity_list[k].getAttribute('type')
            rel_arg_entity_specificity = entity_list[k].getAttribute('specificity')
            entity_mention_list = entity_list[k].getElementsByTagName('entity_mention')
            for m in range((len(entity_mention_list))):
                entity_mention_id = entity_mention_list[m].getAttribute('id')
                if rel_arg_mention_id == entity_mention_id:
                    rel_arg_mention_noun_type = entity_mention_list[m].getAttribute('noun_type')
                    rel_arg_mention_offset = int(entity_mention_list[m].getAttribute('offset'))
                    rel_arg_mention_length = int(entity_mention_list[m].getAttribute('length'))
                    # 上下文信息
                    above = 3
                    below = 3
                    rel_arg_context_dict = find_context(rel_arg_mention_offset, sentences,
                                                         rel_arg_text, above, below)
                    # 拼成一个字符串
                    rel_arg_context = context_dict_to_string(rel_arg_context_dict, above, below)
                    # if rel_arg_context == '':
                    #     print rel_arg_text, rel_arg_id, part_name, rel_arg_context
                    return rel_arg_entity_type, rel_arg_entity_specificity, rel_arg_mention_noun_type, \
                           rel_arg_mention_offset, rel_arg_mention_length, rel_arg_context


# rel_arg的所属filler信息
def rel_arg_filler_info(filler_list, rel_arg_id, rel_arg_text, sentences):
    # 根据id找所在filler和mention
    for k in range((len(filler_list))):
        filler_id = filler_list[k].getAttribute('id')
        if rel_arg_id == filler_id:
            rel_arg_filler_type = filler_list[k].getAttribute('type')
            rel_arg_mention_offset = int(filler_list[k].getAttribute('offset'))
            rel_arg_mention_length = int(filler_list[k].getAttribute('length'))
            # 上下文信息
            above = 3
            below = 3
            rel_arg_context_dict = find_context(rel_arg_mention_offset, sentences,
                                                 rel_arg_text, above, below)
            # 拼成一个字符串
            rel_arg_context = context_dict_to_string(rel_arg_context_dict, above, below)
            # if rel_arg_context == '':
            #     print rel_arg_text, rel_arg_id, part_name, rel_arg_context
            return rel_arg_filler_type, rel_arg_mention_offset, rel_arg_mention_length, rel_arg_context


def extract_relation_each_file(source_filepath, ere_filepath, annotation_filepath, part_name, predict_sources):
    relation_records_each_file = []

    source_fp = open(source_filepath)
    all_source_text = source_fp.read().decode("utf-8")  # 注意编码
    sentences = split_sentences(all_source_text)  # 分句

    ere_file = xml.dom.minidom.parse(ere_filepath)
    ere_root = ere_file.documentElement
    relation_list = ere_root.getElementsByTagName('relation')
    entity_list = ere_root.getElementsByTagName('entity')
    filler_list = ere_root.getElementsByTagName('filler')

    annotation_file = xml.dom.minidom.parse(annotation_filepath)
    annotation_root = annotation_file.documentElement
    annotation_sentiment_list = annotation_root.getElementsByTagName('sentiment_annotations')
    annotation_sentiment_list = annotation_sentiment_list[0]
    annotation_relation_list = annotation_sentiment_list.getElementsByTagName('relation')  # 实际上是relation_mention

    for i in range(len(relation_list)):
        # relation信息
        relation_id = relation_list[i].getAttribute('id')
        relation_type = relation_list[i].getAttribute('type')
        relation_subtype = relation_list[i].getAttribute('subtype')
        relation_mention_list = relation_list[i].getElementsByTagName('relation_mention')

        for j in range(len(relation_mention_list)):
            # relation mention信息
            relation_mention_id = relation_mention_list[j].getAttribute('id')
            relation_mention_realis = relation_mention_list[j].getAttribute('realis')

            # polarity
            for k in range((len(annotation_relation_list))):
                annotation_relation_id = annotation_relation_list[k].getAttribute('ere_id')
                if annotation_relation_id == relation_mention_id:
                    st_em = annotation_relation_list[k].getElementsByTagName('sentiment')
                    # if len(st_em) == 0:
                    #     logger.info("错误：无情感标签。" + " " + part_name + " " + annotation_relation_id +
                    #                 " " + relation_mention_id)
                    label_polarity = st_em[0].getAttribute('polarity')
                    break
            # if label_polarity == 'none':
            #     break  # 如果为none则丢弃该样本

            # rel_arg是entity
            # 基本信息
            rel_arg1 = relation_mention_list[j].getElementsByTagName('rel_arg1')
            rel_arg1 = rel_arg1[0]
            rel_arg1_id = rel_arg1.getAttribute('entity_id')
            rel_arg1_mention_id = rel_arg1.getAttribute('entity_mention_id')
            rel_arg1_role = rel_arg1.getAttribute('role')
            rel_arg1_text = rel_arg1.firstChild.data
            # 所属entity及entity mention信息
            rel_arg1_entity_type, rel_arg1_entity_specificity, rel_arg1_mention_noun_type, rel_arg1_mention_offset, \
            rel_arg1_mention_length, rel_arg1_context = rel_arg_entity_info(entity_list, rel_arg1_id,
                                                                            rel_arg1_mention_id, rel_arg1_text,
                                                                            sentences)

            # rel_arg，同上
            rel_arg2 = relation_mention_list[j].getElementsByTagName('rel_arg2')
            rel_arg2 = rel_arg2[0]
            rel_arg2_role = rel_arg2.getAttribute('role')
            rel_arg2_text = rel_arg2.firstChild.data
            rel_arg2_id = rel_arg2.getAttribute('entity_id')
            if rel_arg2_id != '':
                rel_arg2_mention_id = rel_arg2.getAttribute('entity_mention_id')
                # 所属entity及entity mention信息
                rel_arg2_entity_type, rel_arg2_entity_specificity, rel_arg2_mention_noun_type, rel_arg2_mention_offset, \
                rel_arg2_mention_length, rel_arg2_context = rel_arg_entity_info(entity_list, rel_arg2_id,
                                                                            rel_arg2_mention_id, rel_arg2_text,
                                                                            sentences)
                rel_arg2_is_filler = 0
            else:  # rel_arg2有的不是entity是filler，先简单处理
                rel_arg2_is_filler = 1
                rel_arg2_id = rel_arg2.getAttribute('filler_id')
                # if rel_arg2_id == '':
                #     logger.info("错误：参数不是entity或filler。" + " " + part_name + " " + relation_mention_id)
                rel_arg2_entity_type, rel_arg2_mention_offset, rel_arg2_mention_length, rel_arg2_context = \
                    rel_arg_filler_info(filler_list, rel_arg2_id, rel_arg2_text, sentences)
                rel_arg2_mention_id = ''
                rel_arg2_entity_specificity = ''
                rel_arg2_mention_noun_type = ''

            # trigger
            trigger = relation_mention_list[j].getElementsByTagName('trigger')  # ？待查
            if len(trigger) == 0:
                trigger_offset = ''
                trigger_length = ""
                trigger_text = ""
                trigger_context = ""
            else:
                trigger = trigger[0]
                trigger_offset = int(trigger.getAttribute('offset'))
                trigger_length = int(trigger.getAttribute('length'))
                trigger_text = trigger.firstChild.data
                # 上下文信息
                above = 0
                below = 0  # 可调，考虑trigger中at等词较多，似乎不宜太长上下文，这里先只提取当前句子
                trigger_context_dict = find_context(trigger_offset, sentences, trigger_text, above, below)
                # 拼成一个字符串
                trigger_context = context_dict_to_string(trigger_context_dict, above, below)

            # actual source
            source = st_em[0].getElementsByTagName('source')
            if label_polarity == 'none' or len(source) == 0:
                source_id = ''
                source_offset = 0
                source_length = 0
                source_text = ''
            else:
                source = source[0]
                source_id = source.getAttribute('ere_id')
                source_offset = int(source.getAttribute('offset'))
                source_length = int(source.getAttribute('length'))
                source_text = source.firstChild.data

            # predict source
            offset = rel_arg1_mention_offset
            predict_source = find_source(offset, predict_sources)
            # print predict_source
            if predict_source is not None:
                predict_source_id = predict_source['ere_id']
                predict_source_offset = predict_source['offset']
                predict_source_length = predict_source['length']
                predict_source_text = predict_source['text']
            else:
                predict_source_id = ''
                predict_source_offset = 0
                predict_source_length = 0
                predict_source_text = ''

            relation_record = {
                'file': part_name,
                'relation_id': relation_id, 'relation_type': relation_type, 'relation_subtype': relation_subtype,
                'relation_mention_id': relation_mention_id, 'relation_mention_realis': relation_mention_realis,
                'rel_arg1_id': rel_arg1_id, 'rel_arg1_mention_id': rel_arg1_mention_id,
                'rel_arg1_role': rel_arg1_role, 'rel_arg1_text': rel_arg1_text,
                'rel_arg1_entity_type': rel_arg1_entity_type,
                'rel_arg1_entity_specificity': rel_arg1_entity_specificity,
                'rel_arg1_mention_noun_type': rel_arg1_mention_noun_type,
                'rel_arg1_mention_offset': rel_arg1_mention_offset,
                'rel_arg1_mention_length': rel_arg1_mention_length, 'rel_arg1_context': rel_arg1_context,
                'rel_arg2_id': rel_arg2_id, 'rel_arg2_mention_id': rel_arg2_mention_id,
                'rel_arg2_role': rel_arg2_role, 'rel_arg2_text': rel_arg2_text,
                'rel_arg2_entity_type': rel_arg2_entity_type,
                'rel_arg2_entity_specificity': rel_arg2_entity_specificity,
                'rel_arg2_mention_noun_type': rel_arg2_mention_noun_type,
                'rel_arg2_mention_offset': rel_arg2_mention_offset,
                'rel_arg2_mention_length': rel_arg2_mention_length, 'rel_arg2_context': rel_arg2_context,
                'rel_arg2_is_filler': rel_arg2_is_filler,
                'trigger_offset': trigger_offset, 'trigger_length': trigger_length, 'trigger_text': trigger_text,
                'trigger_context': trigger_context,
                'label_polarity': label_polarity,
                'source_id': source_id, 'source_offset': source_offset, 'source_length': source_length,
                'source_text': source_text,
                'predict_source_id': predict_source_id, 'predict_source_offset': predict_source_offset,
                'predict_source_length': predict_source_length, 'predict_source_text': predict_source_text
            }

            relation_records_each_file.append(relation_record)

    return relation_records_each_file


# em_arg的所属entity信息
def em_arg_entity_info(entity_list, em_arg_id, em_arg_mention_id, em_arg_text, sentences):
    # 根据id找所在entity和mention
    for k in range((len(entity_list))):
        entity_id = entity_list[k].getAttribute('id')
        if em_arg_id == entity_id:
            em_arg_entity_type = entity_list[k].getAttribute('type')
            em_arg_entity_specificity = entity_list[k].getAttribute('specificity')
            entity_mention_list = entity_list[k].getElementsByTagName('entity_mention')
            for m in range((len(entity_mention_list))):
                entity_mention_id = entity_mention_list[m].getAttribute('id')
                if em_arg_mention_id == entity_mention_id:
                    em_arg_mention_noun_type = entity_mention_list[m].getAttribute('noun_type')
                    em_arg_mention_offset = int(entity_mention_list[m].getAttribute('offset'))
                    em_arg_mention_length = int(entity_mention_list[m].getAttribute('length'))
                    # 上下文信息
                    above = 3
                    below = 3
                    em_arg_context_dict = find_context(em_arg_mention_offset, sentences,
                                                         em_arg_text, above, below)
                    # 拼成一个字符串
                    em_arg_context = context_dict_to_string(em_arg_context_dict, above, below)
                    # if em_arg_context == "''":
                    #     print em_arg_text, em_arg_id, part_name, em_arg_context
                    return em_arg_entity_type, em_arg_entity_specificity, em_arg_mention_noun_type, \
                           em_arg_mention_offset, em_arg_mention_length, em_arg_context


# em_arg的所属filler信息
def em_arg_filler_info(filler_list, em_arg_id, em_arg_text, sentences):
    # 根据id找所在filler和mention
    for k in range((len(filler_list))):
        filler_id = filler_list[k].getAttribute('id')
        if em_arg_id == filler_id:
            em_arg_filler_type = filler_list[k].getAttribute('type')
            em_arg_mention_offset = int(filler_list[k].getAttribute('offset'))
            em_arg_mention_length = int(filler_list[k].getAttribute('length'))
            # 上下文信息
            above = 3
            below = 3
            em_arg_context_dict = find_context(em_arg_mention_offset, sentences,
                                                 em_arg_text, above, below)
            # 拼成一个字符串
            em_arg_context = context_dict_to_string(em_arg_context_dict, above, below)
            # if em_arg_context == "''":
            #     print em_arg_text, em_arg_id, part_name, em_arg_context
            return em_arg_filler_type, em_arg_mention_offset, em_arg_mention_length, em_arg_context


def extract_event_each_file(source_filepath, ere_filepath, annotation_filepath, part_name, predict_sources):
    event_records_each_file = []
    em_args_each_file = []

    source_fp = open(source_filepath)
    all_source_text = source_fp.read().decode("utf-8")  # 注意编码
    sentences = split_sentences(all_source_text)  # 分句

    ere_file = xml.dom.minidom.parse(ere_filepath)
    ere_root = ere_file.documentElement
    hopper_list = ere_root.getElementsByTagName('hopper')
    entity_list = ere_root.getElementsByTagName('entity')
    filler_list = ere_root.getElementsByTagName('filler')

    annotation_file = xml.dom.minidom.parse(annotation_filepath)
    annotation_root = annotation_file.documentElement
    annotation_sentiment_list = annotation_root.getElementsByTagName('sentiment_annotations')
    annotation_sentiment_list = annotation_sentiment_list[0]
    annotation_event_list = annotation_sentiment_list.getElementsByTagName('event')

    for i in range(len(hopper_list)):
        # hopper信息
        hopper_id = hopper_list[i].getAttribute('id')
        event_mention_list = hopper_list[i].getElementsByTagName('event_mention')

        for j in range(len(event_mention_list)):
            # event信息
            event_mention_id = event_mention_list[j].getAttribute('id')
            event_mention_type = event_mention_list[j].getAttribute('type')
            event_mention_subtype = event_mention_list[j].getAttribute('subtype')
            event_mention_realis = event_mention_list[j].getAttribute('realis')
            event_mention_ways = event_mention_list[j].getAttribute('ways')

            # polarity
            for k in range((len(annotation_event_list))):
                annotation_event_id = annotation_event_list[k].getAttribute('ere_id')
                if annotation_event_id == event_mention_id:
                    st_em = annotation_event_list[k].getElementsByTagName('sentiment')
                    # if len(st_em) == 0:
                    #     logger.info("错误：无情感标签。" + " " + part_name + " " + annotation_event_id +
                    #                 " " + event_mention_id)
                    label_polarity = st_em[0].getAttribute('polarity')
                    break
            # if label_polarity == 'none':
            #     break  # 如果为none则丢弃该样本

            # trigger
            trigger = event_mention_list[j].getElementsByTagName('trigger')
            trigger = trigger[0]
            trigger_offset = int(trigger.getAttribute('offset'))
            trigger_length = int(trigger.getAttribute('length'))
            trigger_text = trigger.firstChild.data
            # 上下文信息
            above = 3
            below = 3  # 可调
            trigger_context_dict = find_context(trigger_offset, sentences, trigger_text, above, below)
            # 拼成一个字符串
            trigger_context = context_dict_to_string(trigger_context_dict, above, below)

            # em_arg
            em_args = event_mention_list[j].getElementsByTagName('em_arg')
            em_arg_num = len(em_args)
            # print em_arg_num  # 一般不超过4个
            for em_arg in em_args:
                em_arg_role = em_arg.getAttribute('role')
                em_arg_text = em_arg.firstChild.data
                em_arg_id = em_arg.getAttribute('entity_id')
                if em_arg_id != "":  # 是entity
                    em_arg_mention_id = em_arg.getAttribute('entity_mention_id')
                    # 所属entity及entity mention信息
                    em_arg_entity_type, em_arg_entity_specificity, em_arg_mention_noun_type, em_arg_mention_offset, \
                    em_arg_mention_length, em_arg_context = em_arg_entity_info(entity_list, em_arg_id,
                                                                                    em_arg_mention_id, em_arg_text,
                                                                                    sentences)
                    em_arg_is_filler = 0  # 否
                else:
                    em_arg_id = em_arg.getAttribute('filler_id')
                    # if em_arg_id == "":
                    #     logger.info("错误：参数不是entity或filler。" + " " + part_name + " " + event_mention_id)
                    em_arg_entity_type, em_arg_mention_offset, em_arg_mention_length, em_arg_context = \
                        em_arg_filler_info(filler_list, em_arg_id, em_arg_text, sentences)
                    em_arg_mention_id = ""
                    em_arg_entity_specificity = ""
                    em_arg_mention_noun_type = ""
                    em_arg_is_filler = 1
                em_arg_record = {
                    'file': part_name, 'hopper_id': hopper_id, 'event_mention_id': event_mention_id,
                    'em_arg_id': em_arg_id, 'em_arg_mention_id': em_arg_mention_id,
                    'em_arg_role': em_arg_role, 'em_arg_text': em_arg_text,
                    'em_arg_entity_type': em_arg_entity_type,
                    'em_arg_entity_specificity': em_arg_entity_specificity,
                    'em_arg_mention_noun_type': em_arg_mention_noun_type,
                    'em_arg_mention_offset': em_arg_mention_offset,
                    'em_arg_mention_length': em_arg_mention_length, 'em_arg_context': em_arg_context,
                    'em_arg_is_filler': em_arg_is_filler
                }
                em_args_each_file.append(em_arg_record)

            # actual source
            source = st_em[0].getElementsByTagName('source')
            if label_polarity == 'none' or len(source) == 0:
                source_id = ''
                source_offset = 0
                source_length = 0
                source_text = ''
            else:
                source = source[0]
                source_id = source.getAttribute('ere_id')
                source_offset = int(source.getAttribute('offset'))
                source_length = int(source.getAttribute('length'))
                source_text = source.firstChild.data

            # predict source
            offset = trigger_offset
            predict_source = find_source(offset, predict_sources)
            # print predict_source
            if predict_source is not None:
                predict_source_id = predict_source['ere_id']
                predict_source_offset = predict_source['offset']
                predict_source_length = predict_source['length']
                predict_source_text = predict_source['text']
            else:
                predict_source_id = ''
                predict_source_offset = 0
                predict_source_length = 0
                predict_source_text = ''

            event_record = {
                'file': part_name, 'hopper_id': hopper_id, 'event_mention_id': event_mention_id,
                'event_mention_type': event_mention_type, 'event_mention_subtype': event_mention_subtype,
                'event_mention_realis': event_mention_realis, 'event_mention_ways': event_mention_ways,
                'trigger_offset': trigger_offset, 'trigger_length': trigger_length,
                'trigger_text': trigger_text, 'trigger_context': trigger_context,
                'em_arg_num': em_arg_num,
                'label_polarity': label_polarity,
                'source_id': source_id, 'source_offset': source_offset, 'source_length': source_length,
                'source_text': source_text,
                'predict_source_id': predict_source_id, 'predict_source_offset': predict_source_offset,
                'predict_source_length': predict_source_length, 'predict_source_text': predict_source_text
            }

            event_records_each_file.append(event_record)

    return event_records_each_file, em_args_each_file


def write_to_csv(records, filename):
    df = pd.DataFrame(records)
    # logger.debug('记录条数：%d', len(records))
    logger.debug('记录维数：(%d, %d)', df.shape[0], df.shape[1])
    df.to_csv(filename, encoding="utf-8", index=None)


def traverse_and_write_mid_files(source_dir, ere_dir, annotation_dir,
                                 entity_info_dir, relation_info_dir, event_info_dir, em_args_dir):
    ere_suffix = ".rich.ere.xml"
    ere_suffix_length = len(ere_suffix)
    for parent, dirnames, ere_filenames in os.walk(ere_dir):
        for ere_filename in ere_filenames:  # 输出文件信息
            part_name = ere_filename[:-ere_suffix_length]
            source_filepath = source_dir + part_name + ".cmp.txt"
            if os.path.exists(source_filepath) is False: # 不存在，则可能是新闻，xml，先跳过，后续考虑处理
                # source_filepath = source_dir + part_name + ".xml"
                continue
            ere_filepath = ere_dir + ere_filename
            annotation_filepath = annotation_dir + part_name + ".best.xml"
            # 跳过xml，全部188个文件
            # entity
            entity_records, predict_sources = extract_entity_each_file(source_filepath, ere_filepath, annotation_filepath, part_name)
            if len(entity_records) != 0:  # 133个文件有非none样本，全部有样本
                write_to_csv(entity_records, entity_info_dir + part_name + '.csv')
            # relation
            relation_records = extract_relation_each_file(source_filepath, ere_filepath, annotation_filepath, part_name, predict_sources)
            if len(relation_records) != 0:  # 83个文件有非none样本，185个有样本
                write_to_csv(relation_records, relation_info_dir + part_name + '.csv')
            # event
            event_records, em_args = extract_event_each_file(source_filepath, ere_filepath, annotation_filepath, part_name, predict_sources)
            if len(event_records) != 0:  # 112个文件有非none样本，全部有样本
                write_to_csv(event_records, event_info_dir + part_name + '.csv')
                if len(em_args) != 0:  # 实际情况一般都有
                    write_to_csv(em_args, em_args_dir + part_name + '.csv')

if __name__ == '__main__':
    traverse_and_write_mid_files(source_dir, ere_dir, annotation_dir, entity_info_dir,
                                 relation_info_dir, event_info_dir, em_args_dir)
