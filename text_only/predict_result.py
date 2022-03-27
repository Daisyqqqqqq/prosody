import os
from Models import get_model
from torch.nn.parallel import DistributedDataParallel as DDP
import torch
from Models import get_model
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as ticker
from collections import OrderedDict
import math
from espnet_local.nets.pytorch_backend.nets_utils import make_non_pad_mask


def predict_result(best_id, opt):

    test_text_path = './test.txt'
    read_in = read_text(checkpoint=opt.bert_checkpoint, bert_embedding_length=opt.bert_embedding_length)
    _, test_dataset = read_in.read_text_and_label(train_path=None, test_path=test_text_path)
    test_data = Load_audio_and_text_data(dataset=dev_dataset, bert_embedding_length=opt.bert_embedding_length)
    opt.test = DataLoader(dataset=test_data, batch_size=opt.batchsize, shuffle=False, collate_fn=my_collate,
                         num_workers=10, worker_init_fn=worker_init)

    best_model_name = 'epoch_' + str(best_id) + '_final.pth'
    best_model_path = os.path.join(opt.model_save_path, best_model_name)

    print("load model from " + str(best_model_path))

    model = get_model(opt)
    model.load_state_dict(torch.load(best_model_path), strict=True)
    model = torch.nn.DataParallel(model, device_ids=opt.device_ids)
    model = model.cuda()

    model.eval()
    with torch.no_grad():
        for i, batch in enumerate(opt.test):
            attention_mask, input_ids, padded_labels, org_len, mfcc, source, id = batch  # size:batch, length
            attention_mask = attention_mask.cuda()
            input_ids = input_ids.cuda()
            padded_labels = padded_labels.cuda()

            loss, masked_pred_label = model(input_ids=input_ids, attention_mask=attention_mask,
                                            labels=padded_labels)

            loss = loss.sum()

            test_loss += loss.item()

            padded_labels = padded_labels.cpu().numpy().tolist()
            masked_pred_label = masked_pred_label.cpu().numpy().tolist()
            if opt.save_pred_res:
                with open(opt.test_pred_save_path, 'a') as f:
                    for m in range(0, len(masked_pred_label)):
                        f.write(id[m] + '\n')
                        f.write(source[m] + '\n')
                        f.write(str(padded_labels[m][1:org_len[m]-1]) + '\n')
                        f.write(str(masked_pred_label[m][1:org_len[m]-1]) + '\n')
            if opt.save_attention_map:
                for k in range(0, attention_map.size(0)):
                    attention_map_1 = attention_map[k]
                    print(attention_map_1.size())
                    input_ids = [i for i in range(0, 512)]
                    mfcc_mask = [i for i in range(0, attention_map_1.size(-1))]

                    for j in range(0, 8):
                        h = attention_map_1[j].cpu().detach().numpy()
                        df = pd.DataFrame(h, columns=mfcc_mask, index=input_ids)
                        fig = plt.figure()

                        ax = fig.add_subplot(111)

                        cax = ax.matshow(df, interpolation='nearest', cmap='GnBu')
                        fig.colorbar(cax)

                        tick_spacing = df.index.size/5
                        ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
                        ax.yaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

                        ax.set_xticklabels([''] + list(df.columns))
                        ax.set_yticklabels([''] + list(df.index))

                        name = 'batch_' + str(i) + 'text_' + str(k) + '_head_' + str(j) + 'png'
                        plt.savefig(os.path.join(opt.attention_map_save_path, name), bbox_inches='tight')




