# @Author: Ivan
# @Time: 2020/12/23
import argparse
import os
import time

import matplotlib.pyplot as plt
import torch.optim as optim
from torch.utils.data import DataLoader, Subset, ConcatDataset
from torchvision import datasets, transforms

from models import *

parser = argparse.ArgumentParser()
parser.add_argument('-name', type=str, help='project name', default='mnist_qbc')
parser.add_argument('-dataset_path', type=str, help='relative path of dataset', default='../dataset')
parser.add_argument('-batch_size', type=int, help='batch size', default=64)
parser.add_argument('-lr', type=float, help='learning rate', default=0.001)
parser.add_argument('-epochs', type=int, help='training epochs', default=100)
parser.add_argument('-al_epochs', type=int, help='active learning epochs', default=20)
parser.add_argument('-num_classes', type=int, help='number of classes', default=10)
parser.add_argument('-log_dir', type=str, help='log dir', default='output')
args = parser.parse_args()


def load_dataset():
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])

    train_set = datasets.MNIST(
        args.dataset_path, train=True, transform=transform, download=False)
    test_set = datasets.MNIST(
        args.dataset_path, train=False, transform=transform, download=False)
    return train_set, test_set


def create_dataloader():
    train_set, test_set = load_dataset()

    # split trainset into train-val set
    train_set, val_set = torch.utils.data.random_split(train_set, [
        50000, 10000])

    train_loader = DataLoader(
        train_set, batch_size=args.batch_size, shuffle=True)

    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False)

    test_loader = DataLoader(
        test_set, batch_size=args.batch_size, shuffle=False)

    return train_loader, val_loader, test_loader


def train(model, train_loader, optimizer, epoch, device, train_loss_lst, train_acc_lst):
    model.train()  # Set the module in training mode
    correct = 0
    train_loss = 0
    for batch_idx, (inputs, labels) in enumerate(train_loader):
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)

        pred = outputs.max(1, keepdim=True)[1]
        correct += pred.eq(labels.view_as(pred)).sum().item()

        criterion = nn.CrossEntropyLoss()
        loss = criterion(outputs, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        train_loss += loss.item()

        # show batch0 dataset
        # if batch_idx == 0 and epoch == 0:
        #     fig = plt.figure()
        #     inputs = inputs.detach().cpu()  # convert to cpu
        #     grid = utils.make_grid(inputs)
        #     plt.imshow(grid.numpy().transpose((1, 2, 0)))
        #     plt.show()

        # print loss and accuracy
        if (batch_idx + 1) % 50 == 0:
            print('Train Epoch: {} [{}/{} ({:.1f}%)]  Loss: {:.6f}'
                  .format(epoch, batch_idx * len(inputs), len(train_loader.dataset),
                          100. * batch_idx / len(train_loader), loss.item()))

    train_loss /= len(train_loader)  # must divide
    train_loss_lst.append(train_loss)
    train_acc_lst.append(correct / len(train_loader.dataset))
    return train_loss_lst, train_acc_lst


def validate(model, val_loader, device, val_loss_lst, val_acc_lst):
    model.eval()  # Set the module in evaluation mode
    val_loss = 0
    correct = 0
    # no need to calculate gradients
    with torch.no_grad():
        for data, target in val_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)

            criterion = nn.CrossEntropyLoss()
            val_loss += criterion(output, target).item()
            # val_loss += F.nll_loss(output, target, reduction='sum').item()

            # find index of max prob
            pred = output.max(1, keepdim=True)[1]
            correct += pred.eq(target.view_as(pred)).sum().item()

    val_loss /= len(val_loader)
    print('\nVal set: Average loss: {:.6f}, Accuracy: {}/{} ({:.2f}%)\n'
          .format(val_loss, correct, len(val_loader.dataset),
                  100. * correct / len(val_loader.dataset)))

    val_loss_lst.append(val_loss)
    val_acc_lst.append(correct / len(val_loader.dataset))
    return val_loss_lst, val_acc_lst


def test(model, test_loader, device):
    model.eval()  # Set the module in evaluation mode
    test_loss = 0
    correct = 0
    # no need to calculate gradients
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)

            criterion = nn.CrossEntropyLoss()
            test_loss += criterion(output, target).item()

            # find index of max prob
            pred = output.max(1, keepdim=True)[1]
            correct += pred.eq(target.view_as(pred)).sum().item()

    # record loss and acc
    test_loss /= len(test_loader)
    print('Test set: Average loss: {:.6f}, Accuracy: {}/{} ({:.2f}%)\n'
          .format(test_loss, correct, len(test_loader.dataset),
                  100. * correct / len(test_loader.dataset)))
    return test_loss, correct / len(test_loader.dataset)


def main():
    torch.manual_seed(0)
    # create output folder
    now = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    output_path = os.path.join('output', now)
    os.makedirs(output_path)

    # load datasets
    train_loader, val_loader, test_loader = create_dataloader()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = MNISTNet().to(device)
    # model = resnet18(num_classes=10).to(device)

    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9)
    # optimizer = optim.Adam(model.parameters(), lr=lr)

    # train validate and test
    train_loss_lst, val_loss_lst = [], []
    train_acc_lst, val_acc_lst = [], []
    for epoch in range(args.epochs):
        train_loss_lst, train_acc_lst = train(model, train_loader, optimizer,
                                              epoch, device, train_loss_lst, train_acc_lst)
        val_loss_lst, val_acc_lst = validate(
            model, val_loader, device, val_loss_lst, val_acc_lst)
    test(model, test_loader, device)

    # plot loss and accuracy
    fig = plt.figure('Loss and acc')
    plt.plot(range(args.epochs), train_loss_lst, 'g', label='train loss')
    plt.plot(range(args.epochs), val_loss_lst, 'k', label='val loss')
    plt.plot(range(args.epochs), train_acc_lst, 'r', label='train acc')
    plt.plot(range(args.epochs), val_acc_lst, 'b', label='val acc')
    plt.grid(True)
    plt.xlabel('epoch')
    plt.ylabel('acc-loss')
    plt.legend(loc="upper right")
    now = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    plt.savefig(os.path.join(output_path, now + '.png'))
    plt.close(fig)

    # save model
    torch.save(model, os.path.join(output_path, "mnist.pth"))


def al_uncertainty():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # pretrain_model_path = 'mnist.pth'
    # model = torch.load(pretrain_model_path).to(device)
    # model = resnet18(num_classes=10).to(device)
    model = MNISTNet().to(device)

    # create output folder
    now = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    output_path = os.path.join(args.log_dir, now)
    os.makedirs(output_path)

    # load raw dataset
    train_set, test_set = load_dataset()
    inference_batch_size = 1024

    pool = None
    left_trainset = train_set
    left_indices = list(range(len(train_set)))

    # for each trail
    trails = 12
    for trail in range(trails):
        model.eval()
        ranks = []
        # for i in range(len(train_set)):
        #     if i in pool:
        #         continue
        #     data, target = train_set[i]
        #     data = data.to(device)
        #     data.unsqueeze_(0)
        #     output = model(data)
        #     output = F.softmax(output, dim=1)
        #     pred = output.max(1, keepdim=True)
        #     conf = pred[0]
        #     ranks.append((i, conf.detach().cpu().numpy().tolist()[0][0]))
        inference_loader = DataLoader(
            left_trainset, batch_size=inference_batch_size, shuffle=False)

        # inference
        for batch_idx, (inputs, labels) in enumerate(inference_loader):
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            outputs = F.softmax(outputs, dim=1)
            pred = outputs.max(1, keepdim=True)  # pred[0]:conf, pred[1]:index
            conf = pred[0].view(1, -1)[0].detach().cpu().numpy().tolist()
            for i in range(inputs.size(0)):
                ranks.append((batch_idx * inference_batch_size + i, conf[i]))
        print('inference done!')

        ranks.sort(key=lambda x: x[1])  # [(0,0.998),...]
        selected_indices = [item[0] for item in ranks[:5000]]
        print('selected indices!')

        current_selected_trainset = Subset(
            left_trainset, selected_indices)
        if not pool:
            pool = current_selected_trainset
        else:
            pool = ConcatDataset([pool, current_selected_trainset])

        left_indices = [
            i for i in list(range(len(left_indices))) if i not in selected_indices]  # diff set
        left_trainset = Subset(left_trainset, left_indices)
        print('current trainset subed!')

        # ============================retrain===============================
        train_loader = DataLoader(
            pool, batch_size=args.batch_size, shuffle=True)
        test_loader = DataLoader(
            test_set, batch_size=args.batch_size, shuffle=False)

        # choose optimizer
        optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=0.9)
        # optimizer = optim.Adam(model.parameters(), lr=lr)

        # train and test
        train_loss_lst, train_acc_lst = [], []
        for epoch in range(args.al_epochs):
            train_loss_lst, train_acc_lst = train(model, train_loader, optimizer,
                                                  epoch, device, train_loss_lst, train_acc_lst)
        test_loss, test_acc = test(model, test_loader, device)

        # write log file
        with open(os.path.join(output_path, 'log.txt'), 'a') as f:
            f.write("Trail:{}, test loss:{}, test acc:{}\n".format(
                trail, test_loss, test_acc))

        # plot loss and accuracy
        fig = plt.figure('Loss and acc')
        plt.plot(range(args.al_epochs), train_loss_lst, 'g', label='train loss')
        plt.plot(range(args.al_epochs), train_acc_lst, 'r', label='train acc')
        plt.grid(True)
        plt.xlabel('epoch')
        plt.ylabel('loss and acc')
        plt.legend(loc="upper right")
        plt.savefig(os.path.join(output_path, 'trail' + str(trail) + '.png'))
        plt.close(fig)

        # save model
        torch.save(model, os.path.join(
            output_path, "mnist_uncertainty_trail" + str(trail) + ".pth"))
        # ============================retrain===============================


if __name__ == "__main__":
    # main()
    al_uncertainty()
