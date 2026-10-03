import torch, torch.nn as nn, torch.nn.functional as Fn

NEG = -1e9


class Attn(nn.Module):
    def __init__(s, d, h):
        super().__init__(); s.h = h; s.qkv = nn.Linear(d, 3 * d); s.o = nn.Linear(d, d)

    def forward(s, x, bias):
        B, L, d = x.shape
        q, k, v = s.qkv(x).view(B, L, 3, s.h, d // s.h).permute(2, 0, 3, 1, 4)
        y = Fn.scaled_dot_product_attention(q, k, v, attn_mask=bias.unsqueeze(1))
        return s.o(y.transpose(1, 2).reshape(B, L, d))


class Block(nn.Module):
    def __init__(s, d, h, p):
        super().__init__()
        s.n1, s.n2, s.n3 = nn.LayerNorm(d), nn.LayerNorm(d), nn.LayerNorm(d)
        s.tm, s.sp = Attn(d, h), Attn(d, h)
        s.ff = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d)); s.dr = nn.Dropout(p)

    def forward(s, x, M, spatial):
        B, K, T, d = x.shape
        # temporal attention: each sender attends over its own history
        tb = torch.where(M, 0.0, NEG).view(B * K, 1, T).expand(-1, T, -1)
        h = s.n1(x).reshape(B * K, T, d)
        x = x + s.dr(s.tm(h, tb).view(B, K, T, d))
        # spatial attention: at each time step, a sender attends over co-located senders
        if spatial:
            sb = torch.where(M.permute(0, 2, 1), 0.0, NEG).reshape(B * T, 1, K).expand(-1, K, -1)
        else:  # ablation: neighbourhood removed -> each token sees only itself
            sb = torch.where(torch.eye(K, dtype=torch.bool, device=x.device), 0.0, NEG).expand(B * T, -1, -1)
        h = s.n2(x).permute(0, 2, 1, 3).reshape(B * T, K, d)
        x = x + s.dr(s.sp(h, sb).view(B, T, K, d).permute(0, 2, 1, 3))
        return x + s.dr(s.ff(s.n3(x)))


class GRL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lam): ctx.lam = lam; return x.view_as(x)

    @staticmethod
    def backward(ctx, g): return -ctx.lam * g, None


class Detector(nn.Module):
    def __init__(s, fin=8, d=64, h=4, layers=2, T=10, p=0.1, spatial=True):
        super().__init__()
        s.spatial = spatial; s.inp = nn.Linear(fin, d); s.pos = nn.Parameter(torch.zeros(1, 1, T, d))
        s.blocks = nn.ModuleList([Block(d, h, p) for _ in range(layers)])
        s.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        s.dom = nn.Sequential(nn.Linear(d, d), nn.ReLU(), nn.Linear(d, 1))

    def encode(s, X, M):
        x = s.inp(X) + s.pos
        for b in s.blocks: x = b(x, M, s.spatial)
        return x[:, :, -1]                       # (B,K,d) representation at the newest step

    def forward(s, X, M, lam=None):
        z = s.encode(X, M)
        out = s.head(z).squeeze(-1)
        if lam is None: return out
        return out, s.dom(GRL.apply(z, lam)).squeeze(-1)
