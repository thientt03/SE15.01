# coding=utf8
import dxfgrabber
import xml.etree.ElementTree as ET


def find_shape_from_dxf(file_name):
    """
    Đọc tệp DXF và tìm đa giác từ LINE
    :param file_name: Đường dẫn tài liệu
    :return:
    """
    dxf = dxfgrabber.readfile(file_name)
    all_shapes = list()
    new_polygon = dict()
    for e in dxf.entities:
        if e.dxftype == 'LINE':
            # print (e.start, e.end)
            # Tìm một đa giác đóng
            # Dòng không được vẽ theo thứ tự
            end_key = '{}x{}'.format(e.end[0], e.end[1])
            star_key = '{}x{}'.format(e.start[0], e.start[1])
            if end_key in new_polygon:
                # Tìm đa giác đã đóng
                all_shapes.append(new_polygon[end_key])
                new_polygon.pop(end_key)
                continue

            # Chuyển đổi điểm đầu và điểm cuối
            if star_key in new_polygon:
                # Tìm đa giác đã đóng
                all_shapes.append(new_polygon[star_key])
                new_polygon.pop(star_key)
                continue

            # Tìm điểm kết nối
            has_find = False
            for key, points in new_polygon.items():
                if points[-1][0] == e.start[0] and points[-1][1] == e.start[1]:
                    new_polygon[key].append([e.end[0], e.end[1]])
                    has_find = True
                    break
                if points[-1][0] == e.end[0] and points[-1][1] == e.end[1]:
                    new_polygon[key].append([e.start[0], e.start[1]])
                    has_find = True
                    break

            if not has_find:
                new_polygon['{}x{}'.format(e.start[0], e.start[1])] = [
                    [e.start[0], e.start[1]],
                    [e.end[0], e.end[1]],
                ]
    return all_shapes


def find_shape_from_svg(file_name):
    all_shapes = list()
    tree = ET.parse(file_name)
    root = tree.getroot()
    for e in root.findall('{*}polygon'):
        new_polygon = list()
        points = e.get('points').strip().split(' ')
        for point in points:
            p = point.split(',')
            new_polygon.append([float(p[0]), float(p[1])])
        all_shapes.append(new_polygon)

    return all_shapes


def input_polygon(dxf_file):
    """
    :param dxf_file: Địa chỉ tệp
    :param is_class: Trả lại lớp Polygon hoặc danh sách chung
    :return:
    """
    # Trích xuất dữ liệu từ tệp dxf
    datas = find_shape_from_dxf(dxf_file)
    shapes = list()

    for i in range(0, len(datas)):
        shapes.append(datas[i])

    print(shapes)
    return shapes


def input_polygon_svg(svg_file):
    return find_shape_from_svg(svg_file)


if __name__ == '__main__':
    s = find_shape_from_dxf('T2.dxf')
    print(s)
    print(len(s))
