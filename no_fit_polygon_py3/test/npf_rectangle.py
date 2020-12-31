from Polygon import Polygon
import matplotlib.pyplot as plt
import matplotlib.patches as patches

shapes = \
    [
        Polygon(
            [[1168.0, 2.0], [2440.0, 2.0], [2440.0, 668.0], [1168.0, 668.0]]
        )
    ]

# npfs = [
#     Polygon([[3000, 1400], [0, 1400], [0, 0], [3000, 0]]),
# ]

bin_bounds = {'x': 0, 'y': 0, 'width': 2440, 'height': 1220}
bin_polygon = \
    {'points':
        [
            {'x': 2440, 'y': 1220}, {'x': 0, 'y': 1220}, {'x': 0, 'y': 0}, {'x': 2440, 'y': 0}
        ],
        'p_id': '-1',
        'width': 2440,
        'height': 1220
    }

bin_shape = Polygon([[p['x'], p['y']] for p in bin_polygon['points']])

base_width = 16
base_height = base_width * bin_bounds['height'] / bin_bounds['width']
num_bin = len(shapes)
fig_height = num_bin * base_height

fig1 = plt.figure(figsize=(base_width, fig_height))
fig1.suptitle('Polygon packing', fontweight='bold')

i_pic = 1  # Ghi lại chỉ số của bức tranh

# Cài đặt tọa độ
ax = plt.subplot(num_bin, 1, i_pic, aspect='equal')
ax.set_title('NPF')
i_pic += 1
ax.set_xlim(bin_bounds['x'] - 10, bin_bounds['width'] + 50)
ax.set_ylim(bin_bounds['y'] - 10, bin_bounds['height'] + 50)

output_obj = list()
output_obj.append(patches.Polygon(bin_shape.contour(0), fc='#F0E7D3', lw=0.5, edgecolor='#000000'))

for s in shapes:
    output_obj.append(
        patches.Polygon(s.contour(0), fc='#CC9966', lw=0.5, edgecolor='#000000')
    )
#
# for s in npfs:
#     output_obj.append(
#         patches.Polygon(s.contour(0), fc='#CC9966', lw=0.5, edgecolor='#000000')
#     )

for p in output_obj:
    ax.add_patch(p)

plt.show()
