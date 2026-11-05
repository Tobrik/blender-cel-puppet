"""Kaguya v4.1: cut the clean 2x art (art/reference_2x.png) into cel-puppet layers (RGBA PNGs) for the Blender rig.

Layers, back to front: ribbon_L, ribbon_R, body, neck, body_front, head (+ the mouth sprites, from mouths.py).
body_front is the body minus the V opening: the lapels and the dress are in front of the neck, the collar's back
and the chest skin behind it.
Every layer is 2x the reference (1964 x 2824); all coordinates below are REFERENCE px (982 x 1412), scaled on use.
- The art is reference.png through an anime upscaler (upscale.py): clean lines and flat colors, no JPEG noise.
- The hanging locks are cut on their traced outlines (measured row by row on the 2x art), so no collar line, ribbon stripe
  or neck line ever moves with the hair.
- Whatever a layer hides is painted in: the neck (with its outline) under the jaw and the hair; the collar's back, the
  lapel's shadow band, the white lapel and the collar lines under the locks; the ribbons' stripes under the hair.
- Edges against what's behind them are un-mixed into real alpha (no fringes).

usage: python parts.py            (writes parts/*.png at 2x and parts/preview_*.png at 1x)
"""
import os

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "art", "reference_2x.png")
OUT = os.path.join(HERE, "parts")
S = 2                                   # layer px per reference px
H0, W0 = 1412, 982
H, W = H0 * S, W0 * S

def offset_line(pts, d):
    """A polyline moved d px sideways (+ = to the right of its direction of travel, y down)."""
    P = np.asarray(pts, np.float64)
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.stack([-t[:, 1], t[:, 0]], 1)          # right-hand normal on screen (y down)
    return [tuple(p) for p in P + d * n]


# ---------- colors of the clean art (sampled) ----------
INK = (0.012, 0.008, 0.012)
GREY = (0.633, 0.632, 0.645)            # collar back / the lapel's shadow band
LAPEL = (1.0, 0.996, 0.996)

# ---------- regions (reference px, x right, y down) ----------
# the jaw, a few px below its outline: the head is above, the neck below
JAW = [(330, 700), (400, 700), (412, 705), (418, 710), (424, 715), (430, 720), (436, 726), (442, 731), (448, 736),
       (454, 741), (460, 746), (466, 752), (472, 757), (478, 762), (484, 768), (490, 773), (496, 778), (502, 783),
       (508, 788), (514, 793), (520, 797), (526, 801), (532, 803), (538, 803), (544, 803), (550, 802), (556, 801),
       (562, 800), (568, 800), (574, 798.0),
       # the right corner: along the jaw line's own lower edge (it thins from 7 to 4 px toward the ear); the ink pool
       # below it, where the neck's outline joins the jaw in the drawing, is the neck's (JAW_POOL)
       (580, 795.5), (586, 793.4), (592, 791.2), (598, 789.1), (604, 786.9), (610, 784.8), (616, 782.6), (622, 780.5),
       (628, 779.5), (634, 778),
       (640, 776), (646, 774), (652, 772), (658, 770), (664, 767), (670, 766), (676, 764), (682, 761), (688, 758),
       (694, 755), (700, 751), (706, 747), (712, 742), (718, 737), (724, 732), (730, 726), (736, 719), (742, 712),
       (748, 704), (754, 696), (760, 688), (766, 681), (781, 676), (791, 668), (805, 660), (814, 652), (826, 642),
       (846, 636), (900, 636)]
HEAD_TOP = [(900, 636), (982, 636), (982, 0), (0, 0), (0, 700), (330, 700)]
# the ink pool at the right jaw corner (between the jaw line and the neck's outline): it went with the head and stuck out
# as a black spike whenever the head slid / turned off the neck. It's repainted as neck skin + the neck's outline.
JAW_POOL = [(574, 799.5), (580, 799.5), (586, 798.5), (592, 798), (598, 797.5), (604, 797.5), (610, 797),
            (613, 798), (616, 794), (618.5, 789), (620.5, 785), (622.5, 781.5), (622, 780.5), (616, 782.6),
            (610, 784.8), (604, 786.9), (598, 789.1), (592, 791.2), (586, 793.4), (580, 795.5), (574, 798.0)]

# the left lock below the ear: main lock (tip 391,981), the thin strand (tip 413,913), the inner hair over the neck line.
# Traced ~0.6 px outside the outlines; the gaps between them (white, the collar back) are left out.
MAIN_R_EDGE = [  # the main lock's right edge, top to tip
    (366.8, 765), (366.6, 770), (366.9, 775), (366.9, 780), (366.9, 785), (366.6, 790), (366.9, 795), (366.9, 800),
    (366.5, 805), (367.4, 810), (367.4, 815), (367.4, 820), (367.4, 825), (367.9, 830), (368.1, 835), (368.4, 840),
    (368.5, 845), (369.0, 850), (369.4, 855), (369.4, 860), (369.9, 865), (370.4, 870), (371.4, 875), (371.9, 880),
    (372.4, 885), (373.4, 890), (373.9, 895), (374.4, 900), (375.4, 905), (375.9, 910), (376.9, 915), (377.4, 920),
    (378.4, 925), (379.4, 930), (380.4, 935), (381.4, 940), (382.4, 945), (383.4, 950), (385.0, 955), (386.0, 960),
    (387.5, 965), (388.5, 970), (390.0, 975), (391.8, 980.8)]
LOCK_L = [
    (321.6, 560), (411.2, 560), (411.2, 742), (409.8, 748), (407.2, 754.5), (403.5, 753.3), (398.5, 749.8), (394, 746.6),
    (390.2, 743.3), (387.8, 740), (386.3, 737),
    # thin strand, right edge down
    (386.3, 745), (386.7, 755), (387.0, 760), (387.3, 765), (387.7, 770), (388, 775), (388.4, 780), (388.8, 785),
    (389.2, 790), (389.6, 795), (389.7, 800), (390.2, 805), (391.2, 810), (391.6, 815), (392.2, 820), (392.6, 825),
    (393.6, 830), (394.6, 835), (395.2, 840), (396.2, 845), (397.2, 850), (398.2, 855), (399.2, 860), (400.2, 865),
    (401.7, 870), (402.7, 875), (404.2, 880), (405.2, 885), (406.7, 890), (408.2, 895), (409.7, 900), (411.2, 905),
    (413.2, 910), (414.0, 913.5), (412.2, 914.2),
    # thin strand, left edge up
    (409.3, 908), (408.9, 905), (405.9, 900), (403.4, 895), (400.9, 890), (398.4, 885), (396.4, 880), (394.4, 875),
    (392.4, 870), (390.4, 865), (388.4, 860), (386.9, 855), (385.4, 850), (383.9, 845), (382.4, 840), (380.4, 835),
    (379.4, 830), (379.0, 825), (377.4, 820), (375.9, 815), (374.9, 810), (373.4, 805), (372.9, 800), (371.9, 795),
    (370.9, 790), (369.9, 785), (368.9, 780), (368.3, 775), (367.9, 770), (367.2, 765), (367.0, 762.5),
] + MAIN_R_EDGE + [
    # main lock, left edge up
    (387.6, 975), (385.1, 970), (382.1, 965), (379.1, 960), (376.1, 955), (373.1, 950), (371.1, 945), (368.6, 940),
    (366.6, 935), (364.1, 930), (362.1, 925), (359.6, 920), (357.6, 915), (355.6, 910), (353.6, 905), (351.6, 900),
    (350.1, 895), (348.6, 890), (346.6, 885), (345.1, 880), (343.6, 875), (342.1, 870), (341.1, 865), (339.6, 860),
    (338.6, 855), (337.6, 850), (336.1, 845), (335.1, 840), (333.9, 835), (333.1, 830), (332.1, 825), (331.1, 820),
    (330.1, 815), (329.1, 810), (328.1, 805), (327.3, 800), (326.6, 795), (325.6, 790), (325.1, 785), (324.3, 780),
    (323.6, 775), (323.1, 770), (322.6, 765), (322.1, 760), (321.6, 755), (321.1, 750), (321.1, 745), (320.1, 740),
    (319.6, 730), (318.5, 720), (318.1, 710), (318.1, 700), (317.6, 690), (317.1, 680), (316.6, 670), (316.6, 640),
    (317.1, 620), (317.6, 610), (318.1, 600), (318.6, 590), (319.6, 580), (320.1, 570)]

# the right lock below the jaw: strands A (tip 706,951), B (tip 699,1011), C (tip 865,922); white gaps between them left out
LOCK_R = [
    (828.0, 600), (827.3, 640), (826.3, 645), (825.3, 650), (824.3, 655), (823.3, 660), (822.3, 665), (820.8, 670),
    (819.8, 675), (815.7, 680), (815.7, 685), (815.7, 690), (814.7, 695), (813.7, 700), (812.2, 705), (811.2, 710),
    (809.7, 715), (808.2, 720), (806.7, 725), (805.2, 730), (803.7, 735), (802.2, 740), (800.7, 745), (799.2, 750),
    (797.7, 755), (796.2, 760), (794.2, 765), (792.7, 770), (790.7, 775), (789.7, 780), (787.7, 785), (785.8, 790),
    (784.2, 795), (782.2, 800), (780.7, 805), (778.7, 810), (777.2, 815), (775.2, 820), (773.2, 825), (771.2, 830),
    (768.7, 835), (766.7, 840), (764.7, 845), (762.2, 850), (760.2, 855), (757.7, 860), (755.2, 865), (752.7, 870),
    (750.2, 875), (747.7, 880), (745.2, 885), (742.7, 890), (740.2, 895), (737.2, 900), (734.7, 905), (731.7, 910),
    (728.7, 915), (725.7, 920), (722.7, 925), (719.7, 930), (716.2, 935), (712.7, 940), (709.7, 945), (706.2, 950),
    (705.8, 951.5),
    # A, right edge up to the A-B gap
    (708.2, 949), (712.7, 945), (717.7, 940), (722.7, 935), (727.2, 930), (731.7, 925), (735.7, 920), (739.7, 915),
    (743.7, 910), (747.7, 905), (751.5, 900), (755.2, 895), (758.7, 890), (762.0, 885), (765.2, 880), (768.5, 875),
    (771.5, 870), (774.2, 865), (777.2, 860), (777.6, 857.5),
    # B, left edge down
    (777.8, 860), (776.0, 865), (774.2, 870), (772.5, 875), (770.5, 880), (768.7, 885), (766.7, 890), (765.0, 895),
    (762.7, 900), (760.7, 905), (758.5, 910), (756.2, 915), (753.7, 920), (750.7, 925), (748.5, 930), (746.0, 935),
    (743.5, 940), (740.7, 945), (738.0, 950), (735.0, 955), (732.5, 960), (729.5, 965), (726.5, 970), (723.5, 975),
    (720.2, 980), (717.0, 985), (713.7, 990), (710.5, 995), (707.2, 1000), (703.5, 1005), (699.7, 1010),
    (699.4, 1011.5),
    # B, right edge up to the B-C gap
    (702.2, 1009.5), (707.0, 1005), (713.5, 1000), (719.0, 995), (724.5, 990), (730.0, 985), (735.0, 980),
    (739.5, 975), (744.5, 970), (749.0, 965), (753.5, 960), (757.5, 955), (761.5, 950), (765.5, 945), (769.0, 940),
    (772.5, 935), (776.0, 930), (779.8, 925), (783.3, 920), (786.5, 915), (789.5, 910), (792.8, 905), (796.0, 900),
    (799.0, 895), (802.0, 890), (805.0, 885), (807.8, 880), (810.5, 875), (813.3, 870), (815.8, 865), (818.3, 860),
    (820.8, 855), (823.5, 850), (826.0, 845), (828.3, 840), (830.8, 835), (833.0, 830), (835.3, 825), (837.5, 820),
    (839.8, 815), (842.0, 810), (844.0, 805), (846.0, 800), (848.0, 795), (849.8, 790), (850.3, 789),
    # C, left edge down
    (850.7, 790), (850.2, 795), (850.0, 800), (849.7, 805), (849.5, 810), (849.5, 815), (849.7, 820), (850.0, 825),
    (850.0, 835), (850.2, 840), (850.5, 845), (851.0, 850), (851.5, 855), (852.0, 860), (852.5, 865), (853.0, 870),
    (853.7, 875), (854.5, 880), (855.2, 885), (856.2, 890), (857.2, 895), (858.5, 900), (860.0, 905), (861.5, 910),
    (863.0, 915), (864.0, 920), (864.8, 922.5),
    # C, right edge up, and the lock's right edge to the top
    (865.2, 920), (864.7, 915), (864.2, 910), (863.7, 905), (863.5, 900), (863.2, 895), (862.7, 890), (862.7, 870),
    (863.0, 860), (863.2, 855), (863.5, 850), (863.7, 845), (864.0, 840), (864.2, 835), (864.7, 830), (865.2, 825),
    (865.7, 820), (866.2, 815), (867.0, 810), (867.7, 805), (868.2, 800), (869.2, 795), (869.7, 790), (870.7, 785),
    (871.5, 780), (872.2, 775), (873.2, 770), (874.0, 765), (875.0, 760), (876.0, 755), (877.0, 750), (878.0, 745),
    (879.2, 740), (880.2, 735), (881.2, 730), (882.5, 725), (883.5, 720), (884.7, 715), (885.7, 710), (887.0, 705),
    (888.2, 700), (889.5, 695), (890.7, 690), (892.0, 685), (893.5, 680), (894.7, 675), (896.2, 670), (897.2, 665),
    (898.7, 660), (900.2, 655), (901.5, 650), (902.7, 645), (904.2, 640), (905.0, 600)]

# ---- the collar's top edge, one line from the left shoulder, behind the neck, to the right shoulder (centerline).
# Measured where it shows; where a lock or the neck hides it, continued smoothly (drawn only where hidden).
COLLAR_TOP = [
    (170, 893.5), (180, 890.5), (190, 888), (200, 885.5), (210, 883), (220, 880.5), (230, 877.5), (240, 874.5),
    (250, 871.5), (260, 868), (270, 864.5), (280, 860.5), (290, 856.2), (300, 851.5), (310, 846.8), (320, 841.5),
    (330, 835.5), (340, 828.0), (350, 820.4), (360, 812.9), (367.5, 807.2), (372, 803.5),     # under the main lock
    (380, 798.6), (389, 793.75), (395, 792.25), (401, 790.5), (403, 789.8),                  # under the strand, the gap
    (420, 786.5), (450, 783), (480, 781.5), (510, 782), (540, 784.5), (570, 790), (595, 800.5),   # behind the neck
    (610, 814.5), (617.8, 820), (625, 825), (630.5, 830), (634, 835), (637.2, 840), (640.5, 845), (643.5, 850),
    (646.5, 855), (650.5, 860), (655.8, 865), (662, 870), (668.8, 875), (675.5, 880), (682.8, 885), (690.5, 890.6),
    (695, 893.5), (700, 896.5), (705, 899.2), (710, 902.2), (715, 905.2), (720, 908.2), (725, 911),
    (732.5, 914.8), (740, 918.5), (745, 921), (750, 923.5), (762.5, 929.2), (775, 935),        # under A, the gap, under B
    (780, 937.5), (785, 939.8), (790, 942.2), (795, 945.2), (798, 948.5), (798.5, 952), (797.5, 956)]
# the stretches of those lines that show beside a lock (x ranges of COLLAR_TOP; the rest hides under hair / the neck)
COLLAR_TOP_SHOWS = [(160, 336), (364, 376), (386, 404), (608, 731), (736, 755), (771, 800)]
# the dress's top outline on the right shoulder, from the collar's corner
DRESS_TOP = [(797.5, 956), (808, 960), (819, 965), (831, 970), (841.5, 975), (850, 980), (857, 985), (862.5, 990),
             (867, 995), (871, 1000), (874, 1005), (876.7, 1010), (881, 1020), (888, 1040), (893, 1060), (896.5, 1080),
             (898.2, 1100), (898.8, 1130), (898, 1160), (896.8, 1180)]
# the body's silhouette: the left shoulder (outside its outline), the collar top, the dress top, down the right side
BODY_TOP = ([(0, 1100), (62, 1000), (80, 965), (100, 931), (120, 916), (140, 909), (160, 898)]
            + [(x, y - 2.4) for x, y in COLLAR_TOP] + [(x + 1.2, y - 2.2) for x, y in DRESS_TOP[1:]]
            + [(906, 1200), (906, 1412), (0, 1412)])
# the left lapel's V edge (centerline); its top hides under the thin strand up to the collar top
VLINE_L = [(377.0, 800.5), (377.0, 815), (377.2, 830), (376.8, 835), (377.2, 845), (377.5, 850), (379, 860),
           (381, 870), (383.5, 880), (386.8, 890), (390, 900), (393.5, 910), (397, 920), (401, 930), (405.2, 940),
           (409.2, 950), (414, 960), (418.8, 970), (423.8, 980), (429, 990)]
# the lapel's shadow band right of the main lock: its left edge is the lock's edge, then it tapers along the V edge
GREY_BAND_W = 12.5                      # its width beside the V edge (what shows at rest, continued under the lock)
GREY_BAND_L = ([(366.0, 806.6)] + offset_line([p for p in VLINE_L if p[1] <= 915], GREY_BAND_W)[1:]
               + [(378.5, 918.5), (379.7, 920), (383.7, 925), (387.2, 930), (391.2, 935), (395.2, 940), (398.7, 945),
                  (402.7, 950), (407.2, 955), (411.5, 958.5)]
               + [p for p in reversed(VLINE_L) if p[1] <= 950])
# the left lapel: everything left of its V edge (white under the main lock)
LAPEL_L = [(150, 760), (377, 760)] + VLINE_L[1:] + [(440, 1000), (470, 1040), (500, 1105), (150, 1105)]
# the right lapel's inner edge (centerline): the curl beside the neck, then the right V edge down to the V's bottom
VLINE_R = [(616.0, 845), (618.5, 850), (620, 855), (621, 860), (621.2, 865), (621.2, 870), (620.5, 880),
           (619.5, 885), (618.5, 890), (617.5, 895), (616.5, 900), (615, 905), (613.8, 910), (612.2, 915),
           (610.5, 920), (608.8, 925), (607.2, 930), (605.2, 935), (603.5, 940), (601.8, 945), (599.8, 950),
           (597.8, 955), (595.5, 960), (593.5, 965), (591.2, 970), (589, 975), (586.8, 980), (582.2, 990),
           (577.8, 1000), (572.8, 1010), (567.8, 1020), (562.8, 1030), (557.2, 1040), (551.8, 1050), (546.2, 1060),
           (540.8, 1070), (535, 1080), (529.2, 1090), (522.8, 1100), (516.2, 1110)]
VLINE_L_LOW = [(434.8, 1000), (440.2, 1010), (445.8, 1020), (452, 1030), (458.2, 1040), (464.5, 1050),
               (470.8, 1060), (476.8, 1070), (483.2, 1080), (490.2, 1090), (497, 1100), (503.8, 1110)]
V_BOTTOM = (510, 1116)


# the V opening, behind the lapels (the collar's back, the chest skin): there the body is BEHIND the neck, everywhere else
# (the lapels, the dress) the body is in FRONT of it, so the neck slides under the lapels' edges when it bends.
# Its edge runs on the V edges' inner side (the lines stay with the lapels); above 832, where the neck can slide, the
# grey beside the neck under the right collar line is behind it too.
V_OPEN = ([(379.0, 700), (378.6, 800.5)] + offset_line(VLINE_L[1:] + VLINE_L_LOW, -1.6) + [V_BOTTOM]
          + offset_line(list(reversed(VLINE_R)), -1.6)
          + [(640, 847), (637.5, 842.5), (634.5, 837.5), (631, 832.5), (625.5, 827.5), (618, 822.5), (612, 818.5),
             (612, 700)])
# the collar's back, behind the neck (grey, like the bit that shows between the strand and the neck)
COLLAR_BACK = [(377, 800.5), (380, 798.6), (389, 793.75), (395, 792.25), (401, 790.5), (403, 789.8), (420, 786.5),
               (450, 783), (480, 781.5), (510, 782), (540, 784.5), (570, 790), (595, 800.5), (610, 814.5),
               (617.8, 820), (622, 824), (622, 848), (550, 848), (450, 843), (400, 847), (386, 855), (378.5, 861),
               (377.5, 834)]

# ---- the neck: its outline is its own (visible + painted where the jaw / hair hide it); below 832 its left edge is the
# V edge's centerline and below 876 its right edge the right V edge's (that part moves with the body in the rig)
# (under the thin strand it runs on into the V edge at a point, so the collar's back shows as a wedge when the strand
#  swings away; it used to hook into it with a round foot, a grey "bubble")
NECK_LINE_L = [(409.3, 600), (409.3, 690), (409.2, 720), (408.8, 740), (408.3, 750), (407.8, 760), (406.8, 770),
               (405.8, 780), (405.2, 785), (404.7, 790), (403.5, 795), (402, 800.5), (400, 808), (398, 814),
               (396, 819.2), (394, 823.2), (392, 827.5), (390, 832), (388, 836.5), (386, 841), (384, 845.5),
               (382, 850), (380.3, 854), (379.0, 857.5), (378.6, 859)]
# (measured on the art's visible line below the jaw and carried on up under it along its own curve, so the painted part
#  and the art's part meet without a step; down to the collar's curl it's repainted as one line, JOINT_R)
NECK_LINE_R = [(627.8, 600), (627.8, 650), (627.3, 700), (626.3, 730), (625.0, 748), (623.3, 760), (621.0, 770),
               (618.4, 780), (615.9, 788), (614.4, 792), (613.05, 795.5), (611.0, 800), (609.5, 805), (608.25, 810),
               (607.15, 814), (606.25, 818), (605.25, 822), (604.75, 825), (603.75, 830), (603.25, 835),
               (602.75, 840), (602.75, 845), (603.25, 850)]
# where the collar's top line meets the neck's right outline: the neck keeps a clean outline there (the collar line goes
# on behind it, in the body), so nothing of the joint rides on the neck and nothing is notched out of it
JOINT_R = [(597, 794), (617, 794), (612, 846), (597, 846)]
NECK = ([(406.8, 600), (406.8, 740), (406.3, 750), (405.8, 760), (404.8, 770), (403.8, 780), (402.8, 785),
         (402.3, 790), (401.8, 795), (400.3, 800), (399.3, 805), (397.8, 810), (395.8, 815), (393.8, 820),
         (392.1, 824), (390.4, 828), (388.4, 832.5), (386.4, 837), (384.4, 841.5), (382.4, 846), (380.5, 850),
         (379.1, 854), (378.4, 857.5)]
        # (down into the V to 960, all of it moving with the body: the head's shadow can reach that far when she dips)
        + [p for p in VLINE_L if 860 <= p[1] <= 960]
        + [p for p in VLINE_R if 905 <= p[1] <= 960][::-1]
        + [(616.5, 900), (617.5, 895), (618.5, 890), (619.5, 885), (620.5, 880), (619.8, 875), (616.2, 870),
           (611.7, 865), (608.2, 860), (606.7, 855), (605.7, 850), (605.2, 845), (605.2, 840), (605.2, 835),
           (606.2, 830), (607.2, 825), (608.2, 820), (609.5, 815), (610.7, 810), (612.2, 805), (613.7, 800),
           (615.2, 795), (617.9, 788), (620.4, 780), (623, 770), (625.3, 760), (627, 748), (628.3, 730),
           (629.3, 700), (629.8, 650), (629.8, 600)])

# ---- ribbons: what shows, and where each continues, hidden, behind the hair / the head (stripes carried on)
RIBBON_L = [(268, 455), (300, 455), (318, 520), (318, 810), (240, 785), (170, 650), (185, 585)]
RIBBON_L_HIDDEN = [(240, 440), (340, 440), (356, 520), (358, 793.5), (325, 778.5), (240, 745)]
RIBBON_L_EDGE = [(352, 470), (356, 520), (358, 792.5)]
RIBBON_L_BOTTOM = [(318, 774.2), (358, 792.5)]
RIBBON_R = [(650, 800), (660, 772), (671, 763), (700, 745), (729, 724), (760, 690), (766, 683), (781, 678), (791, 670),
            (805, 662), (814, 654), (826, 644), (836, 640), (828, 680), (820, 720), (798, 760), (785, 800), (778, 840),
            (772, 860), (658, 862)]                       # (its bottom stays above the collar line)
RIBBON_R_HIDDEN = [(650, 700), (720, 620), (830, 590), (866, 620), (866, 640), (858, 680), (850, 720), (828, 760),
                   (816, 806.5), (779, 806.5), (770, 780), (700, 740)]
RIBBON_R_EDGE = [(866, 630), (858, 680), (850, 720), (828, 760), (815.5, 805.0)]
RIBBON_R_BOTTOM = [(778, 805.0), (815.5, 805.0)]
# the stripes' direction next to the hair (measured on the art): the hidden part carries them on along it
RIBBON_L_STRIPES = (1.0, 0.36)
RIBBON_R_STRIPES = (1.0, -0.5)
# the ear sits over the ribbon's top; its shading is not ribbon
EAR = [(270, 380), (355, 380), (355, 560), (322, 557), (313, 541), (303, 521), (295, 501), (285, 473), (270, 450)]
# white gaps boxed in by strands / the neck / the ribbon: background
BG_SEEDS = [(396, 770), (369, 790), (645, 830), (757, 900), (822, 655)]
# the original closed mouth (removed from the head; it becomes the CLOSED sprite)
MOUTH_BOX = (500, 640, 655, 716)


# ======================================================================================================================
# helpers (coordinates in reference px; masks / images at 2x)
# ======================================================================================================================

def to2(pts):
    """Reference px -> 2x px (pixel centres)."""
    return np.asarray(pts, np.float64) * S + (S - 1) / 2.0


def poly_mask(pts):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(to2(pts) * 16).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=4)
    return m.astype(bool)


def poly_cover(pts, ss=4):
    """Anti-aliased coverage (0..1) of a polygon, supersampled in its bounding box."""
    P = to2(pts)
    x0, y0 = np.maximum(np.floor(P.min(0)).astype(int) - 2, 0)
    x1, y1 = np.minimum(np.ceil(P.max(0)).astype(int) + 3, [W, H])
    m = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    q = (P - [x0, y0]) * ss + (ss - 1) / 2.0
    cv2.fillPoly(m, [np.round(q * 16).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=4)
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = cv2.resize(m.astype(np.float32) / 255, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    return out


def band(poly, r):
    """Pixels within r (reference px) of a polyline."""
    m = np.zeros((H, W), np.uint8)
    cv2.polylines(m, [np.round(to2(poly) * 16).astype(np.int32)], False, 1,
                  thickness=max(1, int(round(2 * r * S + 1))), lineType=cv2.LINE_8, shift=4)
    return m.astype(bool)


def disk(r):
    k = max(0, int(round(r * S)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))


def dilate(m, r):
    return cv2.dilate(m.astype(np.uint8), disk(r)).astype(bool)


def erode(m, r):
    return cv2.erode(m.astype(np.uint8), disk(r)).astype(bool)


def feather(m, r):
    """A soft version of a mask (0..1), r reference px."""
    s = r * S
    k = int(3 * s) * 2 + 1
    return np.clip(cv2.GaussianBlur(m.astype(np.float32), (k, k), s), 0, 1)


def load():
    return np.array(Image.open(REF).convert("RGB")).astype(np.float32) / 255


def lum(img):
    return img @ np.array([0.299, 0.587, 0.114], np.float32)


def background(img):
    """White connected to the border (plus the boxed-in gaps), with a little tolerance."""
    near_white = (img.min(-1) > 0.93) & ((img.max(-1) - img.min(-1)) < 0.06)
    n, lab = cv2.connectedComponents(near_white.astype(np.uint8), connectivity=4)
    keep = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    for x, y in BG_SEEDS:
        X, Y = np.round(to2([(x, y)])[0]).astype(int)
        assert lab[Y, X] > 0, "background seed (%s, %s) is not on a white pixel" % (x, y)
        keep.add(int(lab[Y, X]))
    keep.discard(0)
    return np.isin(lab, list(keep))


def classes(img):
    L = lum(img)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    chroma = img.max(-1) - img.min(-1)
    red = (r - np.maximum(g, b) > 0.12) & (L < 0.6)
    skin = (r > 0.80) & (r - b > 0.06) & (L > 0.72)
    return dict(red=red, skin=skin, L=L, chroma=chroma)


def nearest_fill(img, known, region):
    """Paint `region` with the color of the nearest `known` pixel."""
    src = (~known).astype(np.uint8)
    _, lab = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    idx = np.zeros(lab.max() + 1, np.int64)
    order = np.nonzero(known.ravel())[0]
    idx[lab.ravel()[order]] = order
    out = img.copy()
    flat = img.reshape(-1, img.shape[-1])
    sel = region & ~known
    out[sel] = flat[idx[lab[sel]]]
    return out


def soften(img, known, region, sigma):
    """Blur `region` with normalized convolution over known | region (sigma in reference px)."""
    s = sigma * S
    m = (known | region).astype(np.float32)
    k = int(3 * s) * 2 + 1
    num = cv2.GaussianBlur(img * m[..., None], (k, k), s)
    den = cv2.GaussianBlur(m, (k, k), s)[..., None]
    out = img.copy()
    out[region] = (num / np.maximum(den, 1e-6))[region]
    return out


def dir_fill(img, known, region, d, max_len=80.0):
    """Paint `region` by carrying `known` colors along direction d (a stripe pattern continues under the hair).
    Whatever no ray reaches gets the nearest known color."""
    d = np.asarray(d, np.float64)
    d = d / np.linalg.norm(d)
    ys, xs = np.nonzero(region & ~known)
    out = img.copy()
    todo = np.ones(len(ys), bool)
    for t in np.arange(0.7, max_len * S, 0.7):
        if not todo.any():
            break
        sel = np.nonzero(todo)[0]
        sy = np.round(ys[sel] - t * d[1]).astype(int)
        sx = np.round(xs[sel] - t * d[0]).astype(int)
        ok = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
        hit = np.zeros(len(sel), bool)
        hit[ok] = known[sy[ok], sx[ok]]
        out[ys[sel[hit]], xs[sel[hit]]] = img[sy[hit], sx[hit]]
        todo[sel[hit]] = False
    if todo.any():
        rest = np.zeros((H, W), bool)
        rest[ys[todo], xs[todo]] = True
        out[rest] = nearest_fill(img, known, rest)[rest]
    return out


def stripe_dir(img, mask):
    """The direction of the stripes inside `mask` (unit vector pointing to +x): the structure tensor's weak axis."""
    L = cv2.GaussianBlur(lum(img), (0, 0), 1.5 * S)
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    J = np.array([[(gx * gx)[mask].sum(), (gx * gy)[mask].sum()], [(gx * gy)[mask].sum(), (gy * gy)[mask].sum()]])
    w, v = np.linalg.eigh(J)
    d = v[:, 0]
    return d if d[0] > 0 else -d


def unmix(c, under, fg, inside=None):
    """Alpha (and straight color) of pixels c = fg blended over `under`. Where fg ~ under the answer is ambiguous:
    1 inside the layer's own shape, 0 outside."""
    d = under - fg
    den = (d * d).sum(-1)
    amb = np.ones(c.shape[:2], np.float32) if inside is None else inside.astype(np.float32)
    a = np.where(den > 0.02, ((under - c) * d).sum(-1) / np.maximum(den, 1e-6), amb)
    a = np.clip(a, 0, 1)
    col = np.where(a[..., None] > 0.15, (c - (1 - a[..., None]) * under) / np.maximum(a[..., None], 1e-3), fg)
    return a, np.clip(col, 0, 1)


def outer_ring(img, bg, r=3, dark=0.3):
    """The anti-aliased pixels on the outside of the outlines: reachable from the background through light pixels
    within r of it (a dark line stops the walk)."""
    walk = bg | (dilate(bg, r) & (lum(img) > dark))
    n, lab = cv2.connectedComponents(walk.astype(np.uint8), connectivity=4)
    ids = np.unique(lab[bg])
    return np.isin(lab, ids[ids > 0]) & ~bg


def matte(img, solid, edge, under, inside=None):
    """RGBA for a layer: `solid` pixels are opaque; `edge` pixels are un-mixed from `under` (what's behind them).
    The foreground color is the nearest dark line pixel when one is close (edges are outlines), else the nearest
    solid pixel; outlines keep the line's own color and let alpha carry the coverage."""
    dark = solid & (lum(img) < 0.25)
    fg = nearest_fill(img, solid, edge)
    near = np.zeros((H, W), bool)
    if dark.any():
        fd = nearest_fill(img, dark, edge)
        dist = cv2.distanceTransform((~dark).astype(np.uint8), cv2.DIST_L2, 3)
        near = dist < 5 * S
        fg = np.where(near[..., None], fd, fg)
    a, col = unmix(img, under, fg, inside)
    col = np.where(near[..., None], fg, col)
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[solid, :3], rgba[solid, 3] = img[solid], 1
    e = edge & ~solid
    rgba[e, :3], rgba[e, 3] = col[e], a[e]
    return rgba


def draw_line(rgba, poly, color, width, mask=None, ss=3):
    """Anti-aliased polyline (width in reference px) painted into an RGBA layer, optionally only where `mask` (0..1)."""
    P = to2(poly)
    pad = int(width * S) + 4
    x0, y0 = np.maximum(np.floor(P.min(0)).astype(int) - pad, 0)
    x1, y1 = np.minimum(np.ceil(P.max(0)).astype(int) + pad, [W, H])
    m = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    q = (P - [x0, y0]) * ss + (ss - 1) / 2.0
    cv2.polylines(m, [np.round(q * 16).astype(np.int32)], False, 255,
                  thickness=max(1, int(round(width * S * ss))), lineType=cv2.LINE_AA, shift=4)
    a = cv2.resize(m.astype(np.float32) / 255, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    if mask is not None:
        a = a * mask[y0:y1, x0:x1]
    col = np.array(color, np.float32)
    sub = rgba[y0:y1, x0:x1]
    sub[..., :3] = col * a[..., None] + sub[..., :3] * (1 - a[..., None])
    sub[..., 3] = a + sub[..., 3] * (1 - a)
    return rgba


def over(layers, base):
    out = base.copy()
    for lay in layers:
        a = lay[..., 3:4]
        out = lay[..., :3] * a + out * (1 - a)
    return out


def save_png(arr, path, mode="RGBA"):
    Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8), mode).save(path)


def preview(layers, name, bg=(0.2, 0.8, 0.9)):
    out = over(layers, np.ones((H, W, 3), np.float32) * np.array(bg, np.float32))
    small = cv2.resize(out, (W0, H0), interpolation=cv2.INTER_AREA)
    save_png(small, os.path.join(OUT, name), "RGB")


# ======================================================================================================================
# the cut
# ======================================================================================================================

def build():
    os.makedirs(OUT, exist_ok=True)
    img = load()
    bg = background(img)
    c = classes(img)
    L = c["L"]
    fg = ~bg
    WHITE = np.ones((H, W, 3), np.float32)
    rows = ((np.arange(H) - (S - 1) / 2.0) / S)[:, None]
    cols = ((np.arange(W) - (S - 1) / 2.0) / S)[None, :]
    outer = outer_ring(img, bg)
    head_reg = poly_mask(JAW + HEAD_TOP)
    below = ~head_reg
    ribL_reg, ribR_reg = poly_mask(RIBBON_L), poly_mask(RIBBON_R)
    ear = poly_mask(EAR)
    neck_reg = poly_mask(NECK)
    # where the collar's top edge comes out from behind the neck, its joint stays with the body
    body_reg = poly_mask(BODY_TOP)
    skin_near = dilate(c["skin"], 3)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    rib_red = (r - np.maximum(g, b) > 0.05) & (L < 0.5)
    light_gray = (L > 0.5) & (c["chroma"] < 0.10)

    # ---- the head: above the jaw (in the ribbons' areas only the ear and the jaw outline), plus the traced locks
    lock_poly = poly_mask(LOCK_L) | poly_mask(LOCK_R)
    lock = lock_poly & fg
    # where a collar / neck line meets a lock, its last pixels inside the trace stay with the body / neck
    body_lines = (band(COLLAR_TOP, 1.9) | band(VLINE_L, 1.9) | (band(NECK_LINE_L, 1.9) & (rows > 753))
                  | band(DRESS_TOP, 1.9))
    line_outside = body_lines & ~lock_poly & (L < 0.3)                  # the lines where they show beside a lock
    lock &= ~(body_lines & ~erode(lock_poly, 0.9) & dilate(line_outside, 1.2))
    trimmed = lock_poly & fg & ~lock & below                            # (they keep the art's own pixels there)
    jaw_keep = c["skin"] | (skin_near & (L < 0.65)) | ((L < 0.3) & ~(r - np.maximum(g, b) > 0.045))
    head_main = head_reg & fg & ~(ribL_reg & ~ear) & ~(ribR_reg & ~jaw_keep) & ~outer & ~lock
    lock_ring = dilate(lock, 1.5) & ~lock & fg & ~head_main            # the locks' soft edge, just outside the trace
    halo = dilate(lock_poly, 2.5) & ~lock_poly                         # + the upscaler's light halo beside the lines
    head_px = head_main | lock
    # (dark pixels there are another part's lines - the V edge, a collar line - and keep the art's own pixels)
    shows = np.zeros((H, W), bool)
    for x0, x1 in COLLAR_TOP_SHOWS:
        shows |= band(COLLAR_TOP, 1.9) & (cols >= x0) & (cols <= x1)
    shows |= band(VLINE_L, 1.9) & (rows >= 832)
    shows |= band(NECK_LINE_L, 1.9) & (rows > 753) & (rows < 822)
    shows |= band(DRESS_TOP, 1.9)
    keep_dark = (lock_ring | halo) & ~lock_poly & ~head_main & (L < 0.15) & shows
    head_cover = head_px | ((lock_ring | halo) & ~keep_dark) | (head_reg & fg)

    # ---- ribbons (behind the head): their pixels, plus their stripes carried on where the head / hair covers them
    ribbons, rib_px = {}, {}
    for name, reg, hid, rims, d in (
            ("ribbon_L", ribL_reg, RIBBON_L_HIDDEN, (RIBBON_L_EDGE, RIBBON_L_BOTTOM), RIBBON_L_STRIPES),
            ("ribbon_R", ribR_reg, RIBBON_R_HIDDEN, (RIBBON_R_EDGE, RIBBON_R_BOTTOM), RIBBON_R_STRIPES)):
        core = reg & fg & (rib_red | (L < 0.3)) & ~skin_near & ~light_gray & ~ear & ~head_px & ~lock_ring
        px = (core | (dilate(core, 2) & reg & fg & ~skin_near & ~light_gray & ~ear)) & ~head_px & ~lock_ring
        rib_px[name] = px
        solid = px & ~outer
        edge = (px | (outer & dilate(core, 3) & reg)) & ~solid
        rgba = matte(img, solid, edge, WHITE)
        # hidden: what the head / hair covers (its soft edge pixels there too, so no see-through seam opens)
        region = poly_mask(hid) & ~solid & dilate(head_cover, 2) & ~(edge & ~dilate(head_cover, 0.5)) & ~bg
        known = solid & ~dilate(head_cover, 2) & ~dilate(bg | outer, 2)
        filled = dir_fill(img, known, region, d)
        filled = soften(filled, known, region, 0.35)
        rgba[region, :3], rgba[region, 3] = filled[region], 1
        print("%s: %d px painted in" % (name, region.sum()))
        # the hidden part's outline, in case the hair uncovers it
        reg_soft = feather(region, 0.6)
        for rim in rims:
            rgba = draw_line(rgba, rim, INK, 3.0, mask=reg_soft)
        ribbons[name] = rgba
    rib_any = rib_px["ribbon_L"] | rib_px["ribbon_R"]

    # ---- neck (in front of the body): skin inside its traced outline; its visible pixels and the rest painted in
    neck_vis = neck_reg & ~dilate(head_reg, 1.5) & fg & ~head_cover & ~outer   # (the jaw line's soft edge: repainted)
    repaint_R = dilate(poly_mask(JAW_POOL), 1.0) | poly_mask(JOINT_R)  # (the jaw corner's ink pool, the collar joint)
    neck_vis &= ~repaint_R
    neck_ring = (dilate(neck_reg, 1.2) & ~neck_reg & below & fg & ~head_cover & ~rib_any
                 & np.where(cols < 500, rows < 831, rows < 875))           # the outline's light side (not the V edges)
    neck_edge_in = neck_reg & below & outer & ~head_cover               # the outline's soft edge inside the trace
    # (no art pixels of the jaw / the collar line ride along at the repainted stretch: its line is the painted one)
    neck_ring &= ~dilate(repaint_R, 2.5)
    neck_edge_in &= ~dilate(repaint_R, 2.5)
    neck_bg = neck_reg & bg & ~head_cover                               # background showing inside the trace: not neck
    neck_cover = (neck_reg & ~neck_bg) | neck_ring

    # ---- body: the silhouette below the collar top; what the locks / neck / head hide is painted in
    # (the neck hides only what's behind it: the V opening; the lapels are in front of it)
    covered = head_cover | (neck_cover & poly_mask(V_OPEN)) | dilate(rib_any, 1)
    body_vis = body_reg & fg & ~covered & ~outer
    hidden = body_reg & covered & ~(outer & ~covered)
    thin = (L < 0.5) & ~cv2.morphologyEx((L < 0.3).astype(np.uint8), cv2.MORPH_OPEN,
                                         np.ones((9 * S, 9 * S), np.uint8)).astype(bool)
    flat_known = body_vis & ~dilate(thin, 2)
    body_img = nearest_fill(img, flat_known, hidden)
    body_img = soften(body_img, flat_known, hidden, 1.5)
    # explicit regions under the hair / the neck (anti-aliased edges)
    lapel_under = hidden & poly_mask(LOCK_L) & poly_mask(LAPEL_L) & ~neck_reg
    body_img[lapel_under] = LAPEL
    chest = hidden & neck_reg
    skin_known = body_vis & c["skin"] & ~dilate(thin, 2)
    body_img[chest] = soften(nearest_fill(img, skin_known, chest), skin_known, chest, 2.0)[chest]
    for poly, color, soft in ((GREY_BAND_L, GREY, 1.2), (COLLAR_BACK, GREY, 0)):
        cov = poly_cover(poly)
        if soft:
            cov = cv2.GaussianBlur(cov, (0, 0), soft * S)
        cov = cov * hidden
        body_img = body_img * (1 - cov[..., None]) + np.array(color, np.float32) * cov[..., None]
    body_img[trimmed & body_reg] = img[trimmed & body_reg]
    body = np.zeros((H, W, 4), np.float32)
    inside = body_vis | hidden
    body[inside, :3], body[inside, 3] = body_img[inside], 1
    edge = body_reg & outer & dilate(body_vis, 3) & ~hidden
    em = matte(img, body_vis, edge, WHITE)
    body[edge] = em[edge]
    # the collar lines where something hides them
    hid_soft = feather(hidden & ~dilate(body_vis & (L < 0.3), 0.5), 0.5)
    body = draw_line(body, COLLAR_TOP, INK, 2.9, mask=hid_soft)
    body = draw_line(body, VLINE_L[:7], INK, 2.8, mask=hid_soft)

    # ---- neck layer
    skin_src = neck_vis & (L > 0.5) & ~dilate(L < 0.3, 2)
    neck_hidden = neck_reg & ~neck_vis & ~neck_edge_in & ~neck_bg
    nimg = nearest_fill(img, skin_src, neck_hidden)
    nimg = soften(nimg, skin_src, neck_hidden, 1.5)
    neck = np.zeros((H, W, 4), np.float32)
    neck[neck_vis, :3], neck[neck_vis, 3] = img[neck_vis], 1
    neck[neck_hidden, :3], neck[neck_hidden, 3] = nimg[neck_hidden], 1
    nh_soft = feather(neck_hidden & ~dilate(neck_vis & (L < 0.3), 0.5), 0.5)
    neck = draw_line(neck, NECK_LINE_L, INK, 3.2, mask=nh_soft)
    # (over the repainted stretch it runs 1.5 px on into the art's own line at both ends: no gap at the handover)
    nr_mask = np.maximum(nh_soft, feather(dilate(repaint_R, 1.5) & neck_reg, 0.5))
    neck = draw_line(neck, NECK_LINE_R, INK, 3.4, mask=nr_mask)
    nt = trimmed & neck_reg
    neck[nt, :3], neck[nt, 3] = img[nt], 1
    # the outline's soft outer edge, un-mixed from what the body shows there
    under_n = over([body], WHITE)
    nedge = neck_ring | neck_edge_in
    nm = matte(img, neck_vis & (L < 0.3), nedge, under_n, inside=np.zeros((H, W), bool))
    neck[nedge] = nm[nedge]

    # ---- head: everything above the jaw (minus the ribbons), plus the traced locks
    under = over([ribbons["ribbon_L"], ribbons["ribbon_R"], body, neck], WHITE)     # what the head sits on
    # (the front body is the same pixels as the body there, so it doesn't change what the head sits on)
    interior = erode(lock_poly, 1.5)
    # the jaw's underside: the head ends where the jaw line ends (its soft edge over the neck; no rim of neck skin)
    jaw_edge = head_main & band(JAW[2:-2], 3.5) & ~erode(head_reg, 3.5) & (L > 0.3) & ~dilate(lock_poly, 1)
    solid = (head_main & ~jaw_edge) | (lock & ((L < 0.3) | interior | head_reg))
    ring_bg = lock_ring & (outer | dilate(bg, 1)) & (L > 0.3)           # (against the other layers it stays theirs)
    head_edge = ((lock & ~solid) | ring_bg | jaw_edge
                 | (outer & dilate(head_px, 3) & (head_reg | lock_poly) & ~(ribL_reg & ~ear) & ~ribR_reg)) & ~solid
    head = matte(img, solid, head_edge, under, inside=(lock_poly | head_reg) & ~jaw_edge)
    # where a lock is cut against another part (not the background), its edge is the trace's own anti-aliased coverage
    cut = lock & ~erode(lock_poly, 1.0) & ~head_reg & ~dilate(bg | outer, 1)
    lock_cov = np.clip(poly_cover(LOCK_L) + poly_cover(LOCK_R), 0, 1)
    head[cut, 3] = np.minimum(head[cut, 3], lock_cov[cut])
    # the jaw line's new lower edge at the right corner runs through ink: give it the cut's own anti-aliased coverage
    corner = dilate(poly_mask(JAW_POOL), 2) & head_reg & (L < 0.3)
    head_cov = poly_cover(JAW + HEAD_TOP)
    head[corner, 3] = np.minimum(head[corner, 3], head_cov[corner])
    # the original mouth comes out (it becomes the CLOSED sprite); skin painted over it
    x0, y0, x1, y1 = [v * S for v in MOUTH_BOX]
    box = np.zeros((H, W), bool)
    box[y0:y1, x0:x1] = True
    ref_skin = np.median(img[y0 - 10 * S:y0 - 2 * S, x0:x1].reshape(-1, 3), 0)
    mouth_px = box & (np.abs(img - ref_skin).sum(-1) > 0.06)
    zone = dilate(mouth_px, 3) & box
    filled = nearest_fill(img, box & ~zone, zone)
    filled = soften(filled, box & ~zone, zone, 1.0)
    closed = np.zeros((H, W, 4), np.float32)
    closed[box, :3] = img[box]
    closed[box, 3] = np.clip((np.abs(img - filled).sum(-1) - 0.02) / 0.10, 0, 1)[box]
    closed[box & ~zone, 3] = 0
    a3 = np.maximum(closed[..., 3:4], 1e-3)
    closed[..., :3] = np.where(closed[..., 3:4] > 0, np.clip((img - (1 - a3) * filled) / a3, 0, 1), 0)
    head[zone, :3] = filled[zone]

    # the body in front of the neck: everything but the V opening (the lapels keep their V edges)
    vopen = poly_cover(V_OPEN)
    body_front = body.copy()
    body_front[..., 3] *= 1 - vopen
    # ... and the body behind the neck is only the V opening (+ a margin under the lapels), so no edge is drawn twice
    body[..., 3] *= dilate(poly_mask(V_OPEN), 3)

    layers = dict(ribbon_L=ribbons["ribbon_L"], ribbon_R=ribbons["ribbon_R"], body=body, neck=neck,
                  body_front=body_front, head=head, mouth_closed=closed)
    order = ("ribbon_L", "ribbon_R", "body", "neck", "body_front", "head", "mouth_closed")
    for name, lay in layers.items():
        save_png(lay, os.path.join(OUT, name + ".png"))
    preview([layers[k] for k in order], "preview_all.png")
    for k in layers:
        preview([layers[k]], "preview_%s.png" % k, bg=(0.85, 0.2, 0.75))
    # the round trip: the layers stacked over white should give back the art
    stack = over([layers[k] for k in order], WHITE)
    err = np.abs(stack - img).max(-1)
    print("round trip: mean err %.4f, px > 0.1: %d" % (err.mean(), (err > 0.1).sum()))
    save_png(cv2.resize(np.clip(err * 4, 0, 1), (W0, H0), interpolation=cv2.INTER_AREA),
             os.path.join(OUT, "debug_roundtrip.png"), "L")
    # every foreground pixel should belong to some layer
    owned = np.zeros((H, W), bool)
    for k in order:
        owned |= layers[k][..., 3] > 0.02
    lost = fg & ~owned & (L < 0.9)
    print("foreground px in no layer: %d" % lost.sum())
    print("parts written to", OUT)


if __name__ == "__main__":
    build()
