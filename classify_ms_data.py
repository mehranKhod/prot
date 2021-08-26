import os
import protease_activity_analysis as paa
import pandas as pd
import argparse
import numpy as np
from analyze_ms_data import load_urine_data

from utils import get_data_dir, get_output_dir

if __name__ == '__main__':
    args = paa.parsing.parse_ms_args()
    data_dir = get_data_dir()
    out_dir = get_output_dir()

    # supply a list of pkl files containing the data to train the classifier
    if args.files is not None:
        files = args.files
    else: # one file generated from reading in single excel file
        mean_scaled, z_scored, plex, renamed, pkl_name_mean, pkl_name_z = \
            load_urine_data(args)
        if args.normalization == 'mean':
            files = [pkl_name_mean]
        if args.normalization == 'zscore':
            files = [pkl_name_z]

    # supply a list of pkl files constituing the independent test set
    if args.test_files is not None:
        test_files = args.test

    # Multiclass classification
    if args.multi_class is not None:
        X, Y, _, X_test, Y_test, _ = paa.data.make_multiclass_dataset(
            data_dir, files,
            args.multi_class,
            args.test_types)

        # independent files for the test dataset
        # NOTE: careful with what is used for test_classes argument here.
        # Assumes that you have specified the independent test data based
        #   on the files. If test_classes != None, those will have been
        #   filtered from the training files. what is the desired behavior
        #   here??
        # Could be combined such that test_files is a specific argument for the
        #   maek classification dataset functions, talk to Melodi about this
        if args.test_files is not None:
            X_test, Y_test, _, _, _ = paa.data.make_multiclass_dataset(
                data_dir, test_files,
                args.multi_class,
                test_types=None)

        for classifier in args.class_type:
            for kernel in args.kernel:
                classifier_name = classifier
                if classifier == 'svm':
                    classifier_name = classifier_name + "_" + kernel

                file_name = args.save_name + "_" + classifier_name
                save_name = os.path.join(out_dir, file_name)
                # set evaluation w/ cross-validation
                val_class_dict, test_class_dict = paa.classify.multiclass_classify(
                    X, Y, classifier, kernel, args.num_folds, save_name,
                    args.scale, args.seed,
                    X_test, Y_test)

    else: # Binary classification with k fold cross validation
        # If args.test_classes = None, X_test, Y_test are None; assumes no
        #   independent sample type filters are provided
        independent_test = (args.test_files is not None) or (args.test_types is not None)

        X, Y, df, X_test, Y_test, df_test = paa.data.make_class_dataset(
            data_dir, files,
            args.pos_classes, args.pos_class,
            args.neg_classes, args.neg_class,
            args.test_types)

        # independent files for the test dataset
        # NOTE: careful with what is used for test_classes argument here.
        # Assumes that you have specified the independent test data based
        #   on the files. If test_classes != None, those will have been
        #   filtered from the training files. what is the desired behavior
        #   here??
        if args.test_files is not None:
            X_test, Y_test, _, _, _, _ = paa.data.make_class_dataset(
                data_dir, test_files,
                args.pos_classes, args.pos_class,
                args.neg_classes, args.neg_class,
                test_types=None)

        for classifier in args.class_type:
            for kernel in args.kernel:
                classifier_name = classifier
                if classifier == 'svm':
                    classifier_name = classifier_name + "_" + kernel

                # evaluation w/ cross-validation
                val_class_dict, test_class_dict = paa.classify.classify_kfold_roc(
                    X, Y, classifier, kernel, args.num_folds, args.pos_class,
                    args.scale, args.seed,
                    X_test, Y_test)

                # cross-validation performance
                tprs_val = val_class_dict["tprs"]
                aucs_val = val_class_dict["aucs"]

                save_name_val = args.save_name + "_crossval_" + classifier_name
                paa.vis.plot_kfold_roc(tprs_val, aucs_val,
                    out_dir, save_name_val, show_sd=True)

                # independent test set performance
                if independent_test:
                    tprs_test = test_class_dict["tprs"]
                    aucs_test = test_class_dict["aucs"]

                    save_name_test = args.save_name + "_test_" + classifier_name
                    paa.vis.plot_kfold_roc(tprs_test, aucs_test,
                        out_dir, save_name_test, show_sd=True)

                # Recursive feature elimination analysis ONLY with rf, lr, linear svm
                if classifier == "svm" and kernel != "linear":
                    break
                paa.classify.recursive_feature_elimination(X, Y,
                    classifier, kernel, args.num_folds, out_dir, save_name_val)
