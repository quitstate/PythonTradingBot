import torch
import torch.nn as nn
import numpy as np


class VAE(nn.Module):
    def __init__(self, input_dim=1, latent_dim=2):
        super(VAE, self).__init__()
        # Encoder
        self.fc1 = nn.Linear(input_dim, 8)
        self.fc21 = nn.Linear(8, latent_dim)  # mean
        self.fc22 = nn.Linear(8, latent_dim)  # logvar
        # Decoder
        self.fc3 = nn.Linear(latent_dim, 8)
        self.fc4 = nn.Linear(8, input_dim)

    def encode(self, x):
        h1 = torch.relu(self.fc1(x))
        return self.fc21(h1), self.fc22(h1)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5*logvar)
        eps = torch.randn_like(std)
        return mu + eps*std

    def decode(self, z):
        h3 = torch.relu(self.fc3(z))
        return self.fc4(h3)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decode(z), mu, logvar


class VAEAnomalyDetector:
    def __init__(self, input_dim=1, latent_dim=2, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = VAE(input_dim, latent_dim).to(self.device)
        self.trained = False

    def fit(self, returns, epochs=100, lr=1e-2):
        returns = np.array(returns).reshape(-1, 1).astype(np.float32)
        data = torch.from_numpy(returns).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        loss_fn = self.vae_loss

        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            recon_batch, mu, logvar = self.model(data)
            loss = loss_fn(recon_batch, data, mu, logvar)
            loss.backward()
            optimizer.step()
        self.trained = True

    def vae_loss(self, recon_x, x, mu, logvar):
        # Reconstruction + KL divergence losses summed over all elements and batch
        recon_loss = nn.functional.mse_loss(recon_x, x, reduction='sum')
        kld = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        return recon_loss + kld

    def anomaly_score(self, value):
        # Reconstruction error as anomaly score
        self.model.eval()
        x = torch.tensor([[value]], dtype=torch.float32).to(self.device)
        with torch.no_grad():
            recon, _, _ = self.model(x)
        return torch.abs(recon - x).item()

    def is_anomaly(self, value, threshold):
        score = self.anomaly_score(value)
        return score > threshold

    def detect_all(self, returns, threshold):
        return [self.is_anomaly(val, threshold) for val in returns]


# Ejemplo de uso:
if __name__ == "__main__":
    # Simula retornos de precios
    returns = [0.001, 0.002, 0.0005, 0.003, 0.04, 0.001, 0.002, 0.05, 0.001, 0.002]
    detector = VAEAnomalyDetector()
    detector.fit(returns, epochs=300)
    # Calcula un threshold simple (por ejemplo, 95 percentil del error de reconstrucción)
    scores = [detector.anomaly_score(r) for r in returns]
    threshold = np.percentile(scores, 95)
    for idx, ret in enumerate(returns):
        print(
            f"Retorno {ret:.4f} "
            f"{'<- ANOMALÍA' if detector.is_anomaly(ret, threshold) else ''} "
            f"(score={scores[idx]:.5f})"
        )
