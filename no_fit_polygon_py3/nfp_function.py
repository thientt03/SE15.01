# -*- coding: utf-8 -*-
from tools import placement_worker, nfp_utls
import math
import json
import random
import copy
from Polygon import Polygon
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pyclipper
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from settings import SPACING, ROTATIONS, BIN_HEIGHT, POPULATION_SIZE, MUTA_RATE

class Nester:
    def __init__(self, container=None, shapes=None):
        """Nester([container,shapes]): Creates a nester object with a container
           shape and a list of other shapes to nest into it. Container and
           shapes must be Part.Faces.
           Typical workflow:
           n = Nester() # creates the nester
           n.add_container(object) # adds a doc object as the container
           n.add_objects(objects) # adds a list of doc objects as shapes
           n.run() # runs the nesting
           n.show() # creates a preview (compound) of the results
           """
        self.container = container  # Hộp đựng linh kiện mang theo
        self.shapes = shapes  # Thông tin thành phần các phần khối
        self.shapes_max_length = 0  # Nói chung vải có chiều dài vô hạn, hãy thiết kế một khổ vải đã xác định kích thước
        self.results = list()  # bộ nhớ cho các kết quả khác nhau
        self.nfp_cache = {}  # Bộ nhớ đệm kết quả tính toán trung gian
        # Các tham số của thuật toán di truyền
        self.config = {
            'curveTolerance': 0.3,  # Sai số tối đa cho phép chuyển đổi Béziers và các đoạn cung. Trong các đơn vị SVG. Dung sai nhỏ hơn sẽ mất nhiều thời gian hơn để tính toán
            'spacing': SPACING,  # Khoảng cách giữa các thành phần
            'rotations': ROTATIONS,  # Mức độ chi tiết của xoay, n phần 360 °, chẳng hạn như: 4 = [0, 90, 180, 270]
            'populationSize': POPULATION_SIZE,  # Số nhóm gen
            'mutationRate': MUTA_RATE,  # Xác suất đột biến
            'useHoles': False,  # Có lỗ hổng? Hiện tại không có lỗ hổng
            'exploreConcave': False,  # Tìm kiếm bề mặt lõm, tạm thời liệu
        }

        self.GA = None  # Thuật toán di truyền Genetic Algorithms
        self.best = None  # Ghi lại kết quả tốt nhất trong di truyền
        self.worker = None  # Theo kết quả NFP, tính toán dữ liệu truyền của mỗi đồ thị
        self.container_bounds = None  # Hình chữ nhật đường bao nhỏ nhất của vùng chứa được sử dụng làm tọa độ của biểu đồ đầu ra

    def add_objects(self, objects):
        """add_objects(objects): adds polygon objects to the nester"""
        if not isinstance(objects, list):
            objects = [objects]
        if not self.shapes:
            self.shapes = []
            
        p_id = 0
        total_area = 0
        for obj in objects:
            points = self.clean_polygon(obj)
            shape = {
                'area': 0,
                'p_id': str(p_id),
                'points': [{'x': p[0], 'y': p[1]} for p in points],
            }
            # Xác định hướng đường thẳng của đa giác
            area = nfp_utls.polygon_area(shape['points'])
            if area > 0:
                shape['points'].reverse()

            shape['area'] = abs(area)
            total_area += shape['area']
            self.shapes.append(shape)

        # Nếu là vải thông thường, kích thước này là bắt buộc
        self.shapes_max_length = total_area / BIN_HEIGHT * 3

    def add_container(self, container):
        """add_container(object): adds a polygon objects as the container"""
        if not self.container:
            self.container = {}

        container = self.clean_polygon(container)

        self.container['points'] = [{'x': p[0], 'y': p[1]} for p in container]
        self.container['p_id'] = '-1'
        xbinmax = self.container['points'][0]['x']
        xbinmin = self.container['points'][0]['x']
        ybinmax = self.container['points'][0]['y']
        ybinmin = self.container['points'][0]['y']

        for point in self.container['points']:
            if point['x'] > xbinmax:
                xbinmax = point['x']
            elif point['x'] < xbinmin:
                xbinmin = point['x']
            if point['y'] > ybinmax:
                ybinmax = point['y']
            elif point['y'] < ybinmin:
                ybinmin = point['y']

        self.container['width'] = xbinmax - xbinmin
        self.container['height'] = ybinmax - ybinmin
        # Đa giác phong bì tối thiểu
        self.container_bounds = nfp_utls.get_polygon_bounds(self.container['points'])

    def clear(self):
        """clear(): Removes all objects and shape from the nester"""
        self.shapes = None

    def run(self):
        """
        -> ['placements'] chính là các tham số dịch chuyển và quay.

        run(): Runs a nesting operation. Returns a list of lists of
        shapes, each primary list being one filled container, or None
        if the operation failed.

        If you open multiple threads, you can design and check the interrupt signal here
        """
        if not self.container:
            print("Empty container. Aborting")
            return
        if not self.shapes:
            print("Empty shapes. Aborting")
            return

        # and still identify the original face, so we can calculate a transform afterwards
        faces = list()

        # Tính toán các h ình cùng với offset của nó, đầu ra sẽ được sử dụng làm placement
        for i in range(0, len(self.shapes)):
            shape = copy.deepcopy(self.shapes[i])
            shape['points'] = self.polygon_offset(
                shape['points'], self.config['spacing']
            )
            faces.append([str(i), shape])
        # build a clean copy so we don't touch the original
        # order by area
        faces = sorted(faces, reverse=True, key=lambda face: face[1]['area'])
        return self.launch_workers(faces)

    def launch_workers(self, adam):
        """
        Quá trình chính, tạo bộ gen, tìm fitness, tìm best fitness
        :param adam:
        :return:
        """

        if self.GA is None:
            # Offset của phôi
            offset_bin = copy.deepcopy(self.container)
            # self.config['spacing'] = 0  # temporary
            offset_bin['points'] = self.polygon_offset(
                self.container['points'], self.config['spacing']
            )

            # Chạy giải thuật di truyền
            self.GA = genetic_algorithm(adam, offset_bin, self.config)
        else:
            self.GA.generation()

        # Tính fitness của mỗi cá thể
        for i in range(0, self.GA.config['populationSize']):
            res = self.find_fitness(self.GA.population[i])
            self.GA.population[i]['fitness'] = res['fitness']
            self.results.append(res)

        # Find the best result
        if len(self.results) > 0:
            best_result = self.results[0]

            for p in self.results:
                if p['fitness'] < best_result['fitness']:
                    best_result = p

            if self.best is None or best_result['fitness'] < self.best['fitness']:
                self.best = best_result

    def find_fitness(self, individual):
        """
        Solve fitness value
        :param individual: 基因组数据
        :return:
        """
        # Gộp các part và thông tin rotation của part
        place_list = copy.deepcopy(individual['placement'])
        rotations = copy.deepcopy(individual['rotation'])
        ids = [p[0] for p in place_list]

        # Nhóm placement với rotation theo thứ tự
        for i in range(0, len(place_list)):
            place_list[i].append(rotations[i])

        nfp_pairs = list()
        new_cache = dict()
        for i in range(0, len(place_list)):
            # Tính toán đa giác nội tiếp của bin và hình
            # Tạo các key theo hình, rotateA, rotateB rồi lưu vào cache
            part = place_list[i]
            key = {
                'A': '-1',
                'B': part[0],
                'inside': True,
                'A_rotation': 0,
                'B_rotation': rotations[i],
            }

            tmp_json_key = json.dumps(key)
            if not tmp_json_key in self.nfp_cache:
                nfp_pairs.append({'A': self.container, 'B': part[1], 'key': key})
            else:
                # Nếu kết quả đã được tính toán
                new_cache[tmp_json_key] = self.nfp_cache[tmp_json_key]

            # Tính toán đa giác ngoại tiếp giữa các hình với nhau sau khi được đưa vào bin
            # Ví dụ: khi hình thứ hai được đưa vào place_list, nó sẽ tạo với hình thứ nhất thành một cặp theo góc quay
            for j in range(0, i):
                placed = place_list[j]
                key = {
                    'A': placed[0],
                    'B': part[0],
                    'inside': False,
                    'A_rotation': rotations[j],
                    'B_rotation': rotations[i],
                }
                tmp_json_key = json.dumps(key)
                if not tmp_json_key in self.nfp_cache:
                    nfp_pairs.append({'A': placed[1], 'B': part[1], 'key': key})
                else:
                    # Nếu kết quả đã được tính toán
                    new_cache[tmp_json_key] = self.nfp_cache[tmp_json_key]

        # only keep cache for one cycle
        self.nfp_cache = new_cache

        # Tính toán thông số dịch chuyển và giá trị fitness
        self.worker = placement_worker.PlacementWorker(
            self.container, place_list, ids, rotations, self.config, self.nfp_cache
        )

        # Tính đa giác tiếp tuyến của tất cả các cặp hình đã tạo
        pair_list = list()
        for pair in nfp_pairs:
            pair_list.append(self.process_nfp(pair))

        # According to these NFPs, solve the graph distribution
        return self.generate_nfp(pair_list)

    def process_nfp(self, pair):
        """
        Tính đa giác tiếp tuyến của tất cả các cặp hình
        :param pair: Tham số kết hợp của hai hình
        :return:
        """
        if pair is None or len(pair) == 0:
            return None

        # Tham số cài đặt, có lỗ hay mặt lõm hay không
        search_edges = self.config['exploreConcave']
        use_holes = self.config['useHoles']

        # Thông số đồ họa, quay các hình theo góc quay
        # A nếu là bin thì không chứa thông tin offset
        A = copy.deepcopy(pair['A'])
        A['points'] = nfp_utls.rotate_polygon(A['points'], pair['key']['A_rotation'])[
            'points'
        ]

        # Là path, chứa thông tin offset
        B = copy.deepcopy(pair['B'])
        # Rotate B theo key pair đã tạo với A
        B['points'] = nfp_utls.rotate_polygon(B['points'], pair['key']['B_rotation'])['points']

        if pair['key']['inside']:
            # Inside or outside
            # Thường thì đây là cặp bin và path, tính NPF của part với bin hoặc giữa các path với nhau
            if nfp_utls.is_rectangle(A['points'], 0.0001):
                # Tính npf của hình với bin
                nfp = nfp_utls.nfp_rectangle(A['points'], B['points'])
            else:
                nfp = nfp_utls.nfp_polygon(A, B, True, search_edges)

            # ensure all interior NFPs have the same winding direction

            # Test_Di chuyển về sát lề
            # for nf in nfp:
            #     for p in nf:
            #         p['x'] = p['x'] - 10
            #         p['y'] = p['y'] - 10

            if nfp and len(nfp) > 0:
                for i in range(0, len(nfp)):
                    if nfp_utls.polygon_area(nfp[i]) > 0:
                        nfp[i].reverse()
            else:
                pass
                # print('NFP Warning:', pair['key'])

        else:
            if search_edges:
                nfp = nfp_utls.nfp_polygon(A, B, False, search_edges)
            else:
                nfp = minkowski_difference(A, B)

            # Kiểm tra xem đa giác NFP có hợp lý không
            if nfp is None or len(nfp) == 0:
                pass
                # print('error in NFP 260')
                # print('NFP Error:', pair['key'])
                # print('A;', A)
                # print('B:', B)
                return None

            for i in range(0, len(nfp)):
                # if search edges is active, only the first NFP is guaranteed to pass sanity check
                if not search_edges or i == 0:
                    if abs(nfp_utls.polygon_area(nfp[i])) < abs(
                            nfp_utls.polygon_area(A['points'])
                    ):
                        pass
                        # print('error in NFP area 269')
                        # print('NFP Area Error: ', abs(nfp_utls.polygon_area(nfp[i])), pair['key'])
                        # print('NFP:', json.dumps(nfp[i]))
                        # print('A: ', A)
                        # print('B: ', B)
                        nfp.pop(i)
                        return None

            if len(nfp) == 0:
                return None
            # for outer NFPs, the first is guaranteed to be the largest.
            # Any subsequent NFPs that lie inside the first are hole
            for i in range(0, len(nfp)):
                if nfp_utls.polygon_area(nfp[i]) > 0:
                    nfp[i].reverse()

                if i > 0:
                    if nfp_utls.point_in_polygon(nfp[i][0], nfp[0]):
                        if nfp_utls.polygon_area(nfp[i]) < 0:
                            nfp[i].reverse()

            # generate nfps for children (holes of parts) if any exist
            # Leave the hole in
            if use_holes and len(A) > 0:
                pass
        return {'key': pair['key'], 'value': nfp}

    def generate_nfp(self, nfp):
        """
        Tính toán tham số dịch chuyển và giá trị fitness của hình
        :param nfp: nfp polygon data
        :return:
        """

        if nfp:
            for i in range(0, len(nfp)):
                if nfp[i]:
                    key = json.dumps(nfp[i]['key'])
                    self.nfp_cache[key] = nfp[i]['value']

        # The worker's nfp cache is only reserved once
        self.worker.nfpCache = copy.deepcopy(self.nfp_cache)
        # self.worker.nfpCache.update(self.nfpCache)
        # Điều chỉnh space với bin ở đây???
        return self.worker.place_paths()

    def show_result(self):
        draw_result(
            self.best['placements'], self.shapes, self.container, self.container_bounds
        )

    def polygon_offset(self, polygon, offset):
        """
        Tạo offset của polygon theo thông số spacing đã cài đặt
        """
        # Chuyển giá trị tọa độ kiểu dict về mảng
        is_list = True
        if isinstance(polygon[0], dict):
            polygon = [[p['x'], p['y']] for p in polygon]
            is_list = False

        # Cài đặt của pycliper
        miter_limit = 2

        co = pyclipper.PyclipperOffset(miter_limit, self.config['curveTolerance'])
        co.AddPath(polygon, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

        result = co.Execute(1 * offset)
        if not is_list:
            result = [{'x': p[0], 'y': p[1]} for p in result[0]]
        return result

    def clean_polygon(self, polygon):
        simple = pyclipper.SimplifyPolygon(polygon, pyclipper.PFT_NONZERO)

        if simple is None or len(simple) == 0:
            return None

        biggest = simple[0]
        biggest_area = pyclipper.Area(biggest)
        for i in range(1, len(simple)):
            area = abs(pyclipper.Area(simple[i]))
            if area > biggest_area:
                biggest = simple[i]
                biggest_area = area

        clean = pyclipper.CleanPolygon(biggest, self.config['curveTolerance'])
        if clean is None or len(clean) == 0:
            return None
        return clean


def draw_result(shift_data, polygons, bin_polygon, bin_bounds):
    """
    从结果中得到平移旋转的数据，把原始图像移到到目标地方，然后保存结果
    Nhận dữ liệu dịch và xoay từ kết quả, di chuyển hình ảnh gốc đến vị trí đích, sau đó lưu kết quả
    :param shift_data: Translation and rotation data
    :param polygons: Raw graphics data
    :param bin_polygon:
    :param bin_bounds:
    :return:
    """
    # Đa giác sản xuất
    shapes = list()
    for polygon in polygons:
        contour = [[p['x'], p['y']] for p in polygon['points']]
        shapes.append(Polygon(contour))

    bin_shape = Polygon([[p['x'], p['y']] for p in bin_polygon['points']])
    shape_area = bin_shape.area(0)

    solution = list()
    rates = list()
    for s_data in shift_data:
        # Một chu trình biểu thị bố cục của vùng chứa
        tmp_bin = list()
        total_area = 0.0
        for move_step in s_data:
            if move_step['rotation'] != 0:
                # Xoay gốc tọa độ
                shapes[int(move_step['p_id'])].rotate(
                    math.pi / 180 * move_step['rotation'], 0, 0
                )
            # Pan
            shapes[int(move_step['p_id'])].shift(move_step['x'], move_step['y'])
            tmp_bin.append(shapes[int(move_step['p_id'])])
            total_area += shapes[int(move_step['p_id'])].area(0)
        # Sử dụng sắp chữ hiện tại
        rates.append(total_area / shape_area)
        solution.append(tmp_bin)
    # kết quả cho thấy
    draw_polygon(solution, rates, bin_bounds, bin_shape)


class genetic_algorithm:
    """
    Thuật toán di truyền
    """

    def __init__(self, adam, bin_polygon, config):
        """
        Khởi tạo các tham số và tạo các cụm gen dựa trên các tham số
        :param adam: Graphics
        :param bin_polygon: Tấm phôi
        :param config: Tham số thuật toán
        """
        self.bin_bounds = bin_polygon['points']
        self.bin_bounds = {
            'width': bin_polygon['width'],
            'height': bin_polygon['height'],
        }
        self.config = config
        self.bin_polygon = bin_polygon
        angles = list()
        shapes = copy.deepcopy(adam)
        for shape in shapes:
            angles.append(self.random_angle(shape))

        # Nhóm gen, thứ tự hình,thông số dịch chuyển và góc quay hình dưới dạng mã gen
        # Đây là cá thể đầu tiên trong quần thể
        self.population = [{'placement': shapes, 'rotation': angles}]

        for i in range(1, self.config['populationSize']):
            # Đột biến
            mutant = self.mutate(self.population[0])
            # Thêm cá thể vào quần thể
            self.population.append(mutant)

    def random_angle(self, shape):
        """
        Lựa chọn góc quay ngẫu nhiên
        :param shape:
        :return:
        """
        angle_list = list()
        for i in range(0, self.config['rotations']):
            angle_list.append(i * (360 / self.config['rotations']))

        # làm rối thứ tự
        def shuffle_array(data):
            for i in range(len(data) - 1, 0, -1):
                j = random.randint(0, i)
                data[i], data[j] = data[j], data[i]
            return data

        angle_list = shuffle_array(angle_list)

        # Kiểm tra xem đồ họa có thể được đặt bên trong sau khi chọn không
        for angle in angle_list:
            rotate_part = nfp_utls.rotate_polygon(shape[1]['points'], angle)
            # Đánh giá xem liệu xoay có nằm ngoài giới hạn hay không, có thể trả lại góc quay nếu không nằm ngoài giới hạn, xoay chỉ cố gắng xoay và không thực sự thay đổi tọa độ đồ họa
            if (
                    rotate_part['width'] < self.bin_bounds['width']
                    and rotate_part['height'] < self.bin_bounds['height']
            ):
                return angle_list[i]

        return 0

    def mutate(self, individual):
        # Đột biến cá thể
        clone = {
            'placement': individual['placement'][:],
            'rotation': individual['rotation'][:],
        }
        for i in range(0, len(clone['placement'])):
            # Đột biến placement của 2 cá thể
            if random.random() < 0.01 * self.config['mutationRate']:
                if i + 1 < len(clone['placement']):
                    clone['placement'][i], clone['placement'][i + 1] = (
                        clone['placement'][i + 1],
                        clone['placement'][i],
                    )
        # Đột biến rotation của 2 cá thể
        if random.random() < 0.01 * self.config['mutationRate']:
            clone['rotation'][i] = self.random_angle(clone['placement'][i])
        return clone

    def generation(self):
        # Fitness thứ tự từ nhỏ đến lớn
        self.population = sorted(self.population, key=lambda a: a['fitness'])
        new_population = [self.population[0]]
        while len(new_population) < self.config['populationSize']:
            male = self.random_weighted_individual()
            female = self.random_weighted_individual(male)
            # Giao phối thế hệ kế tiếp
            children = self.mate(male, female)

            # Đột biến nhỏ
            new_population.append(self.mutate(children[0]))

            if len(new_population) < self.config['populationSize']:
                new_population.append(self.mutate(children[1]))

        # print('new :', new_population)
        self.population = new_population

    def random_weighted_individual(self, exclude=None):
        pop = self.population
        if exclude and pop.index(exclude) >= 0:
            pop.remove(exclude)

        rand = random.random()
        lower = 0
        weight = 1.0 / len(pop)
        upper = weight
        pop_len = len(pop)
        for i in range(0, pop_len):
            if (rand > lower) and (rand < upper):
                return pop[i]
            lower = upper
            upper += 2 * weight * float(pop_len - i) / pop_len
        return pop[0]

    def mate(self, male, female):
        cutpoint = random.randint(0, len(male['placement']) - 1)
        gene1 = male['placement'][:cutpoint]
        rot1 = male['rotation'][:cutpoint]

        gene2 = female['placement'][:cutpoint]
        rot2 = female['rotation'][:cutpoint]

        def contains(gene, shape_id):
            for i in range(0, len(gene)):
                if gene[i][0] == shape_id:
                    return True
            return False

        for i in range(len(female['placement']) - 1, -1, -1):
            if not contains(gene1, female['placement'][i][0]):
                gene1.append(female['placement'][i])
                rot1.append(female['rotation'][i])

        for i in range(len(male['placement']) - 1, -1, -1):
            if not contains(gene2, male['placement'][i][0]):
                gene2.append(male['placement'][i])
                rot2.append(male['rotation'][i])

        return [
            {'placement': gene1, 'rotation': rot1},
            {'placement': gene2, 'rotation': rot2},
        ]


def minkowski_difference(A, B):
    """
    Không gian tiếp tuyến của hai đa giác
    http://www.angusj.com/delphi/clipper/documentation/Docs/Units/ClipperLib/Functions/MinkowskiDiff.htm
    :param A:
    :param B:
    :return:
    """
    Ac = [[p['x'], p['y']] for p in A['points']]
    Bc = [[p['x'] * -1, p['y'] * -1] for p in B['points']]
    solution = pyclipper.MinkowskiSum(Ac, Bc, True)
    largest_area = None
    clipper_nfp = None
    for p in solution:
        p = [{'x': i[0], 'y': i[1]} for i in p]
        sarea = nfp_utls.polygon_area(p)
        if largest_area is None or largest_area > sarea:
            clipper_nfp = p
            largest_area = sarea

    clipper_nfp = [
        {
            'x': clipper_nfp[i]['x'] + Bc[0][0] * -1,
            'y': clipper_nfp[i]['y'] + Bc[0][1] * -1,
        }
        for i in range(0, len(clipper_nfp))
    ]
    return [clipper_nfp]


def draw_polygon_png(solution, bin_bounds, bin_shape, path=None):
    base_width = 8
    base_height = base_width * bin_bounds['height'] / bin_bounds['width']
    num_bin = len(solution)
    fig_height = num_bin * base_height
    fig1 = Figure(figsize=(base_width, fig_height))
    fig1.suptitle('Polygon packing', fontweight='bold')
    FigureCanvas(fig1)

    i_pic = 1  # Ghi lại chỉ số của bức tranh
    for shapes in solution:
        # Cài đặt tọa độ
        ax = fig1.add_subplot(num_bin, 1, i_pic, aspect='equal')
        ax.set_title('Num %d bin' % i_pic)
        i_pic += 1
        ax.set_xlim(bin_bounds['x'] - 10, bin_bounds['width'] + 50)
        ax.set_ylim(bin_bounds['y'] - 10, bin_bounds['height'] + 50)

        output_obj = list()
        output_obj.append(patches.Polygon(bin_shape.contour(0), fc='green'))
        for s in shapes[:-1]:
            output_obj.append(
                patches.Polygon(s.contour(0), fc='yellow', lw=1, edgecolor='m')
            )
        for p in output_obj:
            ax.add_patch(p)

    if path is None:
        path = 'example'

    fig1.savefig('%s.png' % path)


def draw_polygon(solution, rates, bin_bounds, bin_shape):
    # base_width = 25
    # base_height = base_width * bin_bounds['height'] / bin_bounds['width']
    num_bin = len(solution)
    # fig_height = num_bin * base_height
    # fig1 = Figure(figsize=(base_width, fig_height))
    # FigureCanvas(fig1)
    # fig1 = plt.figure(figsize=(base_width, fig_height))
    fig1 = plt.figure(figsize=(25, 13))
    fig1.suptitle('Polygon packing', fontweight='bold')

    # Set lại
    bin_bounds['width'] = 2440
    bin_bounds['height'] = 1220
    i_pic = 1  # Ghi lại index của ảnh
    for shapes in solution:
        # Cài đặt tọa độ
        ax = plt.subplot(num_bin, 1, i_pic, aspect='equal')
        # ax = fig1.set_subplot(num_bin, 1, i_pic, aspect='equal')
        ax.set_title('Num %d bin, rate is %0.4f' % (i_pic, rates[i_pic - 1]))
        i_pic += 1
        ax.set_xlim(bin_bounds['x'] - 10, bin_bounds['width'] + 50)
        ax.set_ylim(bin_bounds['y'] - 10, bin_bounds['height'] + 50)

        output_obj = list()
        output_obj.append(patches.Polygon(bin_shape.contour(0), fc='#c9c4b7'))
        for s in shapes:
            output_obj.append(
                patches.Polygon(s.contour(0), fc='#CC9966', lw=0.5, edgecolor='m')
            )
        for p in output_obj:
            ax.add_patch(p)
    plt.show()
    # fig1.save()


def content_loop_rate(best, n, loop_time=20):
    """
    固定迭代次数
    :param best:
    :param n:
    :param loop_time:
    :return:
    """
    res = best
    run_time = loop_time
    while run_time:
        n.run()
        best = n.best
        print("Fitness: ", best['fitness'])
        if best['fitness'] <= res['fitness']:
            res = best
            # print('change', res['fitness'])
        run_time -= 1

    print("Draw")
    print(best)
    # Cách viền nếu muốn, fucking code
    # for p in res['placements'][0]:
    #     p['y'] -= 8
    #     p['x'] -= 8

    draw_result(res['placements'], n.shapes, n.container, n.container_bounds)


def set_target_loop(best, nest):
    """
    Đặt tất cả đồ họa xuống và thoát
    :param best: Một kết quả đang chạy
    :param nest: Nester class
    :return:
    """
    res = best
    total_area = 0
    rate = None
    num_placed = 0
    step = 0
    while 1:
        print("Loop ", step + 1)
        nest.run()
        best = nest.best
        if best['fitness'] <= res['fitness']:
            res = best
            for s_data in res['placements']:
                tmp_total_area = 0.0
                tmp_num_placed = 0

                for move_step in s_data:
                    tmp_total_area += nest.shapes[int(move_step['p_id'])]['area']
                    tmp_num_placed += 1

                tmp_rates = tmp_total_area / abs(
                    nfp_utls.polygon_area(nest.container['points'])
                )

                if (
                        num_placed < tmp_num_placed
                        or total_area < tmp_total_area
                        or rate < tmp_rates
                ):
                    num_placed = tmp_num_placed
                    total_area = tmp_total_area
                    rate = tmp_rates
        # Tất cả đồ họa bị lỗi trước khi thoát
        if num_placed == len(nest.shapes):
            break
    # Đang vẽ
    draw_result(res['placements'], nest.shapes, nest.container, nest.container_bounds)
