import wandb
import random

def train():
    # Initialize wandb
    wandb.init()
    for i in range(100):
        # Log metrics to wandb
        wandb.log({
            "loss": random.random(),
        })
    
    wandb.finish()

if __name__ == "__main__":
    train() 