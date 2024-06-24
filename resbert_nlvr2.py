# -*- coding: utf-8 -*-
"""resbert_nlvr2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/github/ngruenefeld/MLM-VQA-SoSe24/blob/main/resbert_nlvr2.ipynb
"""

import torch
from torch import nn
from transformers import BertTokenizer, BertModel
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
from torch.nn import BCEWithLogitsLoss, BCELoss
from PIL import Image
from tqdm import tqdm
from datasets import load_dataset
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

# device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(torch.cuda.is_available())

dataset = load_dataset("lmms-lab/NLVR2")

train_dataset = dataset['balanced_dev']
test_dataset = dataset['unbalanced_test_unseen']

first_example = train_dataset[0]
first_example

left_image = first_example['left_image']
right_image = first_example['right_image']
right_image.convert('RGB')
right_image.mode

image_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

question = first_example['question']
question

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

def tokenize_text(text):
    return tokenizer(text, padding='max_length', truncation=True, return_tensors='pt')

# tokenize_text(infer)

class NLVR2Dataset(Dataset):
    def __init__(self, dataset):
        self.dataset = dataset

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        example = self.dataset[idx]

        left_image = example['left_image'].convert('RGB')
        right_image = example['right_image'].convert('RGB')

        left_image = image_transform(left_image)
        right_image = image_transform(right_image)

        text_inputs = tokenize_text(example['question'])

        label = torch.tensor(1.0 if example['answer'] == 'True' else 0.0)

        return left_image, right_image, text_inputs['input_ids'].squeeze(), text_inputs['attention_mask'].squeeze(), label

train_dataset = NLVR2Dataset(dataset['balanced_dev'])
train_dataloader = DataLoader(train_dataset, batch_size=8, shuffle=True)

test_dataset = NLVR2Dataset(dataset['unbalanced_test_unseen'])
test_dataloader = DataLoader(test_dataset, batch_size=8, shuffle=False)

for left_image, right_image, input_ids, attention_mask, label in train_dataloader:
    print(left_image.shape, right_image.shape, input_ids.shape, attention_mask.shape, label.shape)
    break

class MultimodalModel(nn.Module):
    def __init__(self):
        super(MultimodalModel, self).__init__()

        self.resnet = models.resnet50(pretrained=True)
        self.resnet.fc = nn.Linear(self.resnet.fc.in_features, 512)

        self.bert = BertModel.from_pretrained('bert-base-uncased')

        self.classifier = nn.Linear(512 + 512 + 768, 1)

    def forward(self, image_left, image_right, input_ids, attention_mask):
        image_features_left = self.resnet(image_left)
        image_features_right = self.resnet(image_right)

        bert_outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        text_features = bert_outputs.pooler_output

        combined_features = torch.cat((image_features_left, image_features_right, text_features), dim=1)

        output = self.classifier(combined_features)

        return torch.sigmoid(output)

def main():

    model = MultimodalModel().to(device)
    criterion = BCELoss()
    optimizer = Adam(model.parameters(), lr=5e-4)

    epochs = 10

    train_losses = []
    test_losses = []
    test_accuracies = []
    test_aucrocs = []

    best_test_acc = 0.0 # add here

    for epoch in range(epochs):
        model.train()
        total_train_loss = 0
        train_progress_bar = tqdm(train_dataloader, desc=f'Epoch [{epoch+1}/{epochs}] Training')

        for left_image, right_image, input_ids, attention_mask, labels in train_progress_bar:
            # to device
            left_image, right_image = left_image.to(device), right_image.to(device)
            input_ids, attention_mask = input_ids.to(device), attention_mask.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(left_image, right_image, input_ids, attention_mask)
            loss = criterion(outputs.squeeze(), labels)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item()

        avg_train_loss = total_train_loss / len(train_dataloader)
        train_losses.append(avg_train_loss)

        model.eval()
        correct, total = 0, 0
        total_test_loss = 0
        all_labels = []
        all_outputs = []
        test_progress_bar = tqdm(test_dataloader, desc=f'Epoch [{epoch+1}/{epochs}] Testing')

        with torch.no_grad():
            for left_image, right_image, input_ids, attention_mask, labels in test_progress_bar:
                # to device
                left_image, right_image = left_image.to(device), right_image.to(device)
                input_ids, attention_mask = input_ids.to(device), attention_mask.to(device)
                labels = labels.to(device)

                outputs = model(left_image, right_image, input_ids, attention_mask)
                predicted = (outputs.squeeze() > 0.5).float()
                loss = criterion(outputs.squeeze(), labels)
                total_test_loss += loss.item()
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

                all_labels.extend(labels.cpu().numpy())
                all_outputs.extend(outputs.squeeze().cpu().numpy())

        avg_test_loss = total_test_loss / len(test_dataloader)
        avg_test_acc = correct / total

        test_losses.append(avg_test_loss)
        test_accuracies.append(avg_test_acc)

        aucroc = roc_auc_score(all_labels, all_outputs)
        test_aucrocs.append(aucroc)

        print(f'Epoch [{epoch+1}/{epochs}], Train Loss: {avg_train_loss:.4f}, Test Loss: {avg_test_loss:.4f}, Test Accuracy: {avg_test_acc:.4f}, Test AUC-ROC: {aucroc:.4f}')

        if avg_test_acc > best_test_acc:
            best_test_acc = avg_test_acc
            torch.save(model.state_dict(), 'resbert.pth') # change here

    epochs_range = range(1, epochs + 1)

    plt.figure(figsize=(12, 4))

    plt.subplot(1, 2, 1)
    plt.plot(epochs_range, train_losses, label='Train Loss')
    plt.plot(epochs_range, test_losses, label='Test Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title('Training and Test Loss')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(epochs_range, test_accuracies, label='Test Accuracy', color='green')
    plt.plot(epochs_range, test_aucrocs, label='Test AUC-ROC', color='red') #
    plt.xlabel('Epochs')
    plt.ylabel('Evaluation Metrics')
    plt.title('Test Accuracy and AUC-ROC')
    plt.legend()

    plt.tight_layout()
    plt.savefig('resbert_nlvr2.png', dpi=400, bbox_inches='tight', pad_inches=0.1)
    plt.show()

if __name__ == '__main__':
    main()