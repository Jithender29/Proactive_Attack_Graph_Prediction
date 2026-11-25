"""Small PyTorch GraphSAGE-style message-passing model for event-session graphs."""
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

FEATURE_COUNT = 8
MODEL_PATH = Path("models/gnn_model.pt")

class AttackGraphNet(nn.Module):
    def __init__(self, in_features=FEATURE_COUNT, hidden=32):
        super().__init__()
        self.self1 = nn.Linear(in_features, hidden)
        self.neigh1 = nn.Linear(in_features, hidden, bias=False)
        self.self2 = nn.Linear(hidden, hidden)
        self.neigh2 = nn.Linear(hidden, hidden, bias=False)
        self.out = nn.Linear(hidden, 2)

    def forward(self, x, adj):
        # Mean aggregation from neighboring nodes; self-loops are added here.
        a = adj + torch.eye(adj.size(0), device=adj.device)
        a = a / a.sum(dim=1, keepdim=True).clamp(min=1.0)
        h = F.relu(self.self1(x) + self.neigh1(a @ x))
        h = F.dropout(h, p=0.15, training=self.training)
        h = F.relu(self.self2(h) + self.neigh2(a @ h))
        return self.out(h)

def build_synthetic_graphs(count=500, seed=42):
    """Builds labelled toy session graphs to demonstrate the GNN training process."""
    rng = np.random.default_rng(seed)
    graphs = []
    for _ in range(count):
        n = int(rng.integers(5, 13))
        attack = int(rng.random() < 0.45)
        x = rng.normal(0, .25, (n, FEATURE_COUNT)).astype(np.float32)
        # Features: request intensity, failed auth, 4xx, 5xx, admin, suspicious
        # pattern, route novelty, time burst.
        if attack:
            x[:, 0] += rng.uniform(1.0, 3.0)
            x[:, 1] += rng.uniform(.5, 2.0)
            x[:, 2] += rng.uniform(.5, 2.5)
            x[:, 5] += rng.uniform(.5, 2.0)
            x[:, 7] += rng.uniform(.5, 2.0)
        else:
            x[:, 0] += .2
        adj = np.zeros((n, n), dtype=np.float32)
        for i in range(n - 1):
            adj[i, i+1] = adj[i+1, i] = 1
        # A few extra links represent shared session/IP relationships.
        for _ in range(n):
            i, j = rng.integers(0, n, size=2)
            if i != j:
                adj[i, j] = adj[j, i] = 1
        y = np.full(n, attack, dtype=np.int64)
        graphs.append((x, adj, y))
    return graphs

def train_gnn(epochs=35, model_path=MODEL_PATH):
    torch.manual_seed(42)
    graphs = build_synthetic_graphs()
    model = AttackGraphNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003, weight_decay=1e-4)
    for epoch in range(epochs):
        model.train()
        losses = []
        for x, adj, y in graphs:
            xt = torch.tensor(x)
            at = torch.tensor(adj)
            yt = torch.tensor(y)
            optimizer.zero_grad()
            logits = model(xt, at)
            loss = F.cross_entropy(logits, yt)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"[GNN] epoch {epoch+1:02d}/{epochs} loss={np.mean(losses):.4f}")
    path = Path(model_path); path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "feature_count": FEATURE_COUNT}, path)
    print(f"[SAVED] {path.resolve()}")
    return model

def load_gnn(model_path=MODEL_PATH):
    ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
    model = AttackGraphNet(in_features=ckpt["feature_count"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model

def score_graph(model, features, adjacency):
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(features, dtype=torch.float32),
                       torch.tensor(adjacency, dtype=torch.float32))
        return torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
