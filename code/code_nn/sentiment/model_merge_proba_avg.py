# coding=utf-8

from cnn import *
from sklearn_svm import *


def compute_average_proba(proba1, proba2):
    proba = []
    for i in range(len(proba1)):
        proba.append([(proba1[i][0] + proba2[i][0])/2, (proba1[i][1] + proba2[i][1])/2])
    return proba

if __name__ == '__main__':
    mode = True

    # 读取各文件中间信息
    print 'Read data...'
    df_file_records, nw_file_records = \
        read_file_info_records(ere_dir, entity_info_dir, relation_info_dir, event_info_dir, em_args_dir)
    print 'DF files:', len(df_file_records), ' NW files:', len(nw_file_records)

    # DF全部作为训练数据，NW分成训练和测试数据, 合并训练的NW和DF，即可用原来流程进行训练测试
    if mode is True:
        print '*** DF ***'
        print 'Split into train and test dataset...'
        portion = 0.8
        trainnum = int(len(df_file_records) * 0.8)
        train_files = df_file_records[:trainnum]
        test_files = df_file_records[trainnum:]
    else:
        print '*** NW ***'
        print 'Merge and split into train and test dataset...'
        portion = 0.2
        nw_trainnum = int(len(nw_file_records) * portion)
        train_files = df_file_records + nw_file_records[:nw_trainnum]
        test_files = nw_file_records[nw_trainnum:]

    # 预处理和提取标签
    print 'Labels extraction...'
    train_files = without_none(train_files)  # 训练文件去掉none的样本
    y_train = get_merged_labels(train_files)  # 只有1,2两类
    y_test = get_merged_labels(test_files)  # 0,1,2三类
    print 'Train data number:', len(y_train)
    print 'Test data number:', len(y_test)
    print 'Train labels:', y_train
    print 'Test labels:', y_test

    # cnn
    print 'CNN:'
    # 训练部分
    # 提取特征及标签
    total_clip_length = 56
    embeddings_index, dim = read_embedding_index(glove_100d_path)
    print 'Train samples extraction...'
    train_files = without_none(train_files)  # 训练文件去掉none的样本
    x_train = gen_cnn_features(train_files, embeddings_index, dim, total_clip_length)  # 提取特征
    y_train_cnn = [y-1 for y in y_train]  # 改为0,1
    x_train, y_train_cnn = convert_samples(x_train, y_train_cnn)  # 转换为通道模式
    print 'Train...'
    model = cnn_fit(x_train, y_train_cnn)  # 分正负
    # 测试部分
    # 提取特征及标签
    print 'Test samples extraction...'
    x_test = gen_cnn_features(test_files, embeddings_index, dim, total_clip_length)  # 提取特征
    x_test, y_test = convert_samples(x_test, y_test)
    y_test = y_test.tolist()
    # 测试
    print 'Test...'
    y_proba_cnn = model.predict(x_test)

    # svm
    print 'SVM:'
    # 提取特征
    print "Features extraction..."
    x_all = gen_sklearn_features(train_files, test_files) # 提取特征
    # 特征分割训练测试集
    trainlen = len(y_train)
    x_train = x_all[:trainlen]
    x_test = x_all[trainlen:]
    # 训练
    print 'Train...'
    clf = svm.SVC(probability=True)
    clf.fit(x_train, y_train)
    joblib.dump(clf, 'svm_model.m')  # 保存训练模型
    # 测试
    print 'Test...'
    clf = joblib.load('svm_model.m')
    y_proba_svm = clf.predict_proba(x_test)

    # 输出概率取平均值
    print 'Take average probabilities of all models: '
    y_proba = compute_average_proba(y_proba_cnn, y_proba_svm)
    print y_proba
    y_predict = predict_by_proba(y_proba, 0.4)  # 0.5就全0了，0.4还行

    # 评价
    print 'Evalution: '
    print 'Test labels: ', y_test
    # print 'Filter labels:', y_predict1
    print 'Predict labels: ', y_predict
    evaluation_3classes(y_test, y_predict)  # 3类的测试评价

    # 测试结果写入记录
    test_files = to_dict(test_files)
    test_files = attach_predict_labels(test_files, y_predict)

    # 寻找源
    print 'Find sources... '
    test_files = find_sources(test_files, source_dir, ere_dir)
    # test_files = use_annotation_source(test_files)

    # 写入文件
    print 'Write into best files...'
    write_best_files(test_files, predict_dir)




