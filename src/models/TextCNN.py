import torch
import torch.nn as nn
import torch.nn.functional as F
from TimeDistributed import TimeDistributed

class TextCNN(nn.Module):
    def __init__(self, embed_mat, opt):
        super(TextCNN, self).__init__()
        self.opt = opt
        
        V = opt['embed_num']
        D = opt['embed_dim']
        embedding = torch.from_numpy(embed_mat)
        C = opt['class_num']
        Ci = 1
        Co = opt['kernel_num']
        Ks = opt['kernel_sizes']
        
        self.embed = nn.Embedding(V, D)
        self.embed.weight.data.copy_(embedding)
        
        self.tdfc1 = nn.Linear(D, 512)
        self.td1 = TimeDistributed(self.tdfc1)
        self.tdbn1 = nn.BatchNorm2d(1)
        
        self.tdfc2 = nn.Linear(D, 512)
        self.td2 = TimeDistributed(self.tdfc2)
        self.tdbn2 = nn.BatchNorm2d(1)

        self.convs1 = nn.ModuleList([nn.Conv2d(Ci, Co, (K, 512)) for K in Ks])
        self.convbn1 = nn.ModuleList([nn.BatchNorm2d(Co) for i in range(len(Ks))])
        self.convs2 = nn.ModuleList([nn.Conv2d(Ci, Co, (K, 512)) for K in Ks])
        self.convbn2 = nn.ModuleList([nn.BatchNorm2d(Co) for i in range(len(Ks))])

        self.fc1 = nn.Linear(len(Ks)*Co*2, 512)
        self.bn1 = nn.BatchNorm1d(512)
        self.fc2 = nn.Linear(512, C)
        
    def forward(self, x, y):
        x = self.embed(x.long())
        if self.opt['static']:
            x = x.detach()
        x = F.relu(self.tdbn1(self.td1(x).unsqueeze(1)))

        y = self.embed(y.long())
        if self.opt['static']:
            y = y.detach()
        y = F.relu(self.tdbn2(self.td2(y).unsqueeze(1)))
        
        x = [F.relu(self.convbn1[i](conv(x))).squeeze(3) for i, conv in enumerate(self.convs1)]
        x = [F.max_pool1d(i, i.size(2)).squeeze(2) for i in x]
        x = torch.cat(x, 1)
        
        y = [F.relu(self.convbn2[i](conv(y))).squeeze(3) for i, conv in enumerate(self.convs2)]
        y = [F.max_pool1d(i, i.size(2)).squeeze(2) for i in y]
        y = torch.cat(y, 1)
        
        x = torch.cat((x, y), 1)

        x = F.relu(self.bn1(self.fc1(x)))
        logit = self.fc2(x)
        return logit