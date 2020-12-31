# -*- coding: utf-8 -*-
from nfp_function import Nester, content_loop_rate, set_target_loop
from tools import input_utls
from settings import BIN_WIDTH, BIN_NORMAL, BIN_CUT_BIG


if __name__ == '__main__':
    n = Nester()
    s = input_utls.input_polygon('test_file/E6.dxf')
    # s = input_utls.input_polygon_svg('test_file/test1.svg')
    n.add_objects(s)

    if n.shapes_max_length > BIN_WIDTH:
        BIN_NORMAL[2][0] = n.shapes_max_length
        BIN_NORMAL[3][0] = n.shapes_max_length

    # Chọn vải mặt
    n.add_container(BIN_NORMAL)
    # Chạy tính toán
    n.run()

    # Điều kiện thoát thiết kế
    res_list = list()
    best = n.best
    # Đặt trong một thùng chứa
    # Placed in a container
    # set_target_loop(best, n)    # T6

    # Chu kỳ một số lần cụ thể
    # Cycle a certain number of times
    content_loop_rate(best, n, loop_time=20)  # T7 , T4
