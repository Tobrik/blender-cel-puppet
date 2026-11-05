"""Clean 4x anime upscale of one image on the CPU (Real-ESRGAN x4plus anime 6B), then down to the wanted scale.

usage: python upscale.py <in.png> <out.png> <model.pth> [out_scale=2] [threads=4]
Model (17 MB): https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth
Needs torch (the CPU build is enough), numpy, pillow. Tiled (256 px) so RAM stays small; torch is limited to a few
threads so the machine stays usable; ~75 s for a 1000x1400 image on 4 threads. No GPU used.
Writes <out>_4x.png (the raw 4x result) and <out> (Lanczos to out_scale x).
"""
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image


class RDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        return self.conv5(torch.cat((x, x1, x2, x3, x4), 1)) * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf, gc=32):
        super().__init__()
        self.rdb1, self.rdb2, self.rdb3 = RDB(nf, gc), RDB(nf, gc), RDB(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nb=6, nf=64):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def upscale(img, net, tile=256, pad=16):
    h, w, _ = img.shape
    x = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0)
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    for y0 in range(0, h, tile):
        for x0 in range(0, w, tile):
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            py0, px0, py1, px1 = max(y0 - pad, 0), max(x0 - pad, 0), min(y1 + pad, h), min(x1 + pad, w)
            with torch.no_grad():
                o = net(x[:, :, py0:py1, px0:px1])[0].clamp(0, 1).numpy().transpose(1, 2, 0)
            oy, ox = (y0 - py0) * 4, (x0 - px0) * 4
            out[y0 * 4:y1 * 4, x0 * 4:x1 * 4] = o[oy:oy + (y1 - y0) * 4, ox:ox + (x1 - x0) * 4]
    return out


def main(inp, outp, model, scale=2, threads=4):
    torch.set_num_threads(int(threads))
    net = RRDBNet()
    sd = torch.load(model, map_location="cpu", weights_only=True)
    net.load_state_dict(sd.get("params_ema", sd.get("params", sd)))
    net.eval()
    im = Image.open(inp)
    rgb = np.asarray(im.convert("RGB"), np.float32) / 255
    t = time.time()
    big = upscale(rgb, net)
    print("4x done in %.0f s" % (time.time() - t))
    big8 = Image.fromarray((big * 255).round().astype(np.uint8))
    big8.save(outp.replace(".png", "_4x.png"))
    s = int(scale)
    if s != 4:
        big8 = big8.resize((im.width * s, im.height * s), Image.LANCZOS)
    big8.save(outp)
    print("saved", outp, big8.size)


if __name__ == "__main__":
    main(*sys.argv[1:])
