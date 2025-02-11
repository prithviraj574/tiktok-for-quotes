import torch
import torch.nn as nn

total_quotes = 10000

class UserTower(nn.Module):
    def __init__(self):
        super().__init__()
        # 128 > 64 > 32
        self.embedding = nn.Embedding(200, 128)
        self.mlp = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
        )
        
    def forward(self, user_ids):
        return self.mlp(self.embedding(user_ids))
    

class QuoteTower(nn.Module):
    def __init__(self, num_quote_ids=10000):
        super().__init__()
        
        # Dynamic content-aware embedding based on quote id
        self.dynamic_embed = nn.Embedding(num_quote_ids, 128)
        
        self.dynamic_fc = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32)
        )
        # Load static author embeddings
        self.author_embed = nn.Embedding(num_quote_ids, 384)
        self.author_embed.load_state_dict(torch.load('../models/author_embeddings.pth'))
        self.author_embed.weight.requires_grad = False  # Keep embeddings frozen
        self.author_fc =  nn.Sequential(
            nn.Linear(384, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
        # Load static quote embeddings
        self.quote_embed = nn.Embedding(num_quote_ids, 384)
        self.quote_embed.load_state_dict(torch.load('../models/quote_embeddings.pth'))
        self.quote_embed.weight.requires_grad = False  # Keep embeddings frozen
        self.quote_fc =  nn.Sequential(
            nn.Linear(384, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
        # Combined MLP processing. The concatenated features are:
        # - Adjusted static quote embedding: 64
        # - Dynamic quote id embedding: 32
        # - Static author embedding: author_embedding_dim
        combined_dim = 128*2 + 32
        self.mlp = nn.Sequential(
            nn.Linear(combined_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
        )
    def forward(self, quote_ids):
        """
        Args:
            quote_ids (Tensor): Quote ID indices (batch_size,)
        
        Returns:
            Tensor: Output features (batch_size, 128)
        """
        # Retrieve frozen static quote embedding and process it
        static_quote = self.quote_embed(quote_ids)  # (batch_size, 384)
        static_quote = self.quote_fc(static_quote)  # (batch_size, 128)
        # Retrieve frozen static author embedding and process it
        static_author = self.author_embed(quote_ids)  # (batch_size, 384)
        static_author = self.author_fc(static_author)  # (batch_size, 128)
        # Retrieve dynamic quote embedding and process it
        dynamic_quote = self.dynamic_embed(quote_ids)  # (batch_size, 512)
        dynamic_quote = self.dynamic_fc(dynamic_quote)  # (batch_size, 128)
        # Concatenate all features (128 + 128 + 128 = 384)
        combined = torch.cat([static_quote, static_author, dynamic_quote], dim=1)
        # Process through MLP
        return self.mlp(combined)  # (batch_size, 128)

class TwoTowerModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.user_tower = UserTower()
        self.quote_tower = QuoteTower()
        
    def forward(self, user_ids, quote_ids):
        user_embeds = self.user_tower(user_ids)
        quote_embeds = self.quote_tower(quote_ids)
        return (user_embeds * quote_embeds).sum(dim=1)  # Dot product

class UserRecommender(nn.Module):
    def __init__(self,precomputed_quote_embeds=torch.zeros((total_quotes,32)),trained_user_tower=UserTower()):
        """
        Args:
            precomputed_quote_embeds (Tensor): Precomputed quote embeddings of shape (num_quotes, embedding_dim)
        """
        super().__init__()
        self.user_tower = trained_user_tower  # Trainable user tower.
        # Register precomputed quote embeddings as a buffer so they are not updated during training.
        self.register_buffer('quote_embeds', precomputed_quote_embeds)
    
    def forward(self, user_ids, quote_ids):
        """
        Args:
            user_ids (Tensor): User IDs of shape (batch_size,)
            quote_ids (Tensor): Quote IDs of shape (batch_size,)
        
        Returns:
            scores (Tensor): Dot product scores of shape (batch_size,)
        """
        # Compute user embeddings using the trainable user tower.
        user_embeds = self.user_tower(user_ids)  # (batch_size, embedding_dim)
        # Retrieve fixed quote embeddings using the provided quote IDs.
        quote_embeds = self.quote_embeds[quote_ids]  # (batch_size, embedding_dim)
        # Compute dot product similarity.
        scores = (user_embeds * quote_embeds).sum(dim=1)
        return scores
