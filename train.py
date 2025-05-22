import wandb
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import time
def get_model():
    return nn.Sequential(
        nn.Linear(784, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )

def train():
    # Initialize wandb
    wandb.init()
    config = wandb.config
    
    # Generate fake data
    num_samples = 10000
    fake_data = torch.randn(num_samples, 784)  # Random features
    fake_labels = torch.randint(0, 10, (num_samples,))  # Random labels 0-9
    
    # Create dataset and dataloader
    train_dataset = TensorDataset(fake_data, fake_labels)
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
    
    # Create model and optimizer
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = get_model().to(device)
    optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.CrossEntropyLoss()
    
    # Training loop
    for epoch in range(1000):
        for data, target in train_loader:
            data = data.to(device)
            target = target.to(device)
            
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            wandb.log({
                "loss": loss.item(),
                "epoch": epoch
            })
    
    wandb.finish()

if __name__ == "__main__":
    train()