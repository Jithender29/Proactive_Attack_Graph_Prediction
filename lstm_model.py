"""PyTorch LSTM for next application attack-surface category prediction."""
from pathlib import Path
import numpy as np
import torch
from torch import nn

CATEGORIES = ["home", "products", "search", "login", "cart", "checkout", "orders", "admin", "api", "other"]
MODEL_PATH = Path("models/lstm_model.pt")
SEQ_LEN = 6

class NextTargetLSTM(nn.Module):
    def __init__(self, vocab_size=len(CATEGORIES), embedding=24, hidden=48):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding)
        self.lstm = nn.LSTM(embedding, hidden, batch_first=True, num_layers=1)
        self.fc = nn.Linear(hidden, vocab_size)

    def forward(self, x):
        emb = self.embedding(x)
        out, _ = self.lstm(emb)
        return self.fc(out[:, -1, :])

def make_sequences(samples=5000, seed=42):
    """Generate reproducible labelled route sequences for a demonstrable first model."""
    rng = np.random.default_rng(seed)
    sequences, targets = [], []
    normal = [0, 1, 2, 3, 4, 1, 5, 6, 0]
    attack_patterns = [
        [0, 1, 2, 3, 3, 3, 9, 9, 3],      # repeated authentication probing
        [1, 2, 2, 2, 9, 9, 1, 8, 8],      # API/endpoint enumeration
        [0, 1, 8, 8, 8, 7, 7, 7, 7],      # API to admin probing
        [1, 1, 2, 9, 9, 8, 8, 5, 5],      # discovery then checkout probing
    ]
    for _ in range(samples):
        if rng.random() < .45:
            base = attack_patterns[int(rng.integers(0, len(attack_patterns)))]
            seq = [int(v if rng.random() > .08 else rng.integers(0, len(CATEGORIES))) for v in base]
        else:
            seq = [int(v if rng.random() > .08 else rng.integers(0, len(CATEGORIES))) for v in normal]
        start = int(rng.integers(0, len(seq) - SEQ_LEN))
        part = seq[start:start+SEQ_LEN+1]
        sequences.append(part[:-1]); targets.append(part[-1])
    return torch.tensor(sequences, dtype=torch.long), torch.tensor(targets, dtype=torch.long)

def train_lstm(epochs=25, model_path=MODEL_PATH):
    torch.manual_seed(42)
    X, y = make_sequences()
    model = NextTargetLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    criterion = nn.CrossEntropyLoss()
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(len(X))
        losses = []
        for ids in order.split(128):
            optimizer.zero_grad()
            logits = model(X[ids])
            loss = criterion(logits, y[ids])
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"[LSTM] epoch {epoch+1:02d}/{epochs} loss={np.mean(losses):.4f}")
    path = Path(model_path); path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "categories": CATEGORIES,
                "seq_len": SEQ_LEN}, path)
    print(f"[SAVED] {path.resolve()}")
    return model

def load_lstm(model_path=MODEL_PATH):
    ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
    model = NextTargetLSTM(vocab_size=len(ckpt["categories"]))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt["categories"], ckpt["seq_len"]

def predict_next(model, categories, route_sequence):
    ids = [categories.index(x) if x in categories else categories.index("other")
           for x in route_sequence[-SEQ_LEN:]]
    if len(ids) < SEQ_LEN:
        ids = [categories.index("other")] * (SEQ_LEN-len(ids)) + ids
    with torch.no_grad():
        probs = torch.softmax(model(torch.tensor([ids], dtype=torch.long)), dim=1)[0]
    idx = int(torch.argmax(probs))
    return categories[idx], float(probs[idx])
