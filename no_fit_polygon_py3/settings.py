# -*- coding: utf-8 -*-

POPULATION_SIZE = 10  # Số bộ gen
MUTA_RATE = 20  # Xác suất đột biến
ROTATIONS = 2  # Xoay lựa chọn, 1: Không thể xoay
# Đơn vị là MM (mm)
SPACING = 4 # Khoảng trống đồ họa
# Kích thước vải khác nhau
BIN_HEIGHT = 1220
BIN_WIDTH = 2440
BIN_NORMAL = [
    [0, 0],
    [0, BIN_HEIGHT],
    [BIN_WIDTH, BIN_HEIGHT],
    [BIN_WIDTH, 0],
]  # Vải chung là vô hạn
BIN_CUT_BIG = [[0, 0], [0, 1570], [2500, 1570], [2500, 0]]  # Máy cắt cỡ 1
BIN_CUT_SMALL = [[0, 0], [0, 1200], [1500, 1200], [1500, 0]]  # # Máy cắt cỡ 2
