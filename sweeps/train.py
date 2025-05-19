import wandb
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

def get_model(model_type, num_layers):
    if model_type == "default":
        return nn.Sequential(
            nn.Linear(784, 128),
            nn.ReLU(),
            nn.Linear(128, 10)
        )
    elif model_type == "cnn":
        return nn.Sequential(
            nn.Conv2d(1, 32, 3),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(1600, 10)
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")

def train():
    # Initialize wandb
    wandb.init()
    
    # Get hyperparameters from wandb config
    config = wandb.config
    model_type = config.model_type
    learning_rate = config.learning_rate
    batch_size = config.batch_size
    num_epochs = config.num_epochs
    optimizer_name = config.optimizer
    weight_decay = config.weight_decay
    num_layers = config.num_layers
    
    # Load MNIST dataset
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    train_dataset = datasets.MNIST('data', train=True, download=True, transform=transform)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Create model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = get_model(model_type, num_layers).to(device)
    
    # Setup optimizer
    if optimizer_name == "adam":
        optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    else:  # sgd
        optimizer = optim.SGD(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    
    criterion = nn.CrossEntropyLoss()
    
    # Training loop
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
            total += target.size(0)
            
            if batch_idx % 100 == 0:
                wandb.log({
                    "loss": loss.item(),
                    "accuracy": 100. * correct / total,
                    "epoch": epoch,
                    "batch": batch_idx
                })
    
    wandb.finish()

if __name__ == "__main__":
    train() 