# SE15.01
# GOALS
Thực hiện thuật toán áp dụng trong thực tế ván cắt lát công nghiệp. Mục tiêu cố gắng tiết kiệm chi phí nhất có thể để tạo lời lớn nhất cho bên sản xuất. Thực hiện các thuật toán liên quan đánh giá khả năng sử dụng cũng như hoạt động vào thực tế

# Nesting là gì ??
Chúng tôi muốn gói tất cả các chữ cái thành hình vuông, sử dụng ít vật liệu nhất có thể. Nếu một hình vuông duy nhất là không đủ, chúng tôi cũng muốn giảm thiểu số lượng hình vuông được sử dụng.
Trong thế giới CNC này được gọi là " nesting ", và phần mềm mà thực hiện điều này thường nhắm vào khách hàng công nghiệp và rất tốn kém.

# Sử dụng
Đảm bảo rằng tất cả các phần đã được chuyển đổi thành đường viền và không có đường viền nào chồng chéo lên nhau.

# Sơ lược thuật toán
Mặc dù tồn tại các phương pháp phỏng đoán tốt cho vấn đề đóng gói thùng hình chữ nhật, nhưng trong thế giới thực, chúng ta quan tâm đến các hình dạng bất thường.

Chiến lược này bao gồm hai phần:

chiến lược vị trí (ví dụ: làm cách nào để tôi đưa từng phần vào thùng?)
và chiến lược tối ưu hóa (tức là thứ tự chèn tốt nhất là gì?)

# Đặt bộ phận
Quỹ đạo kết quả là NFP. NFP chứa tất cả các vị trí có thể có của B chạm vào các phần đã đặt trước đó. Sau đó, chúng ta có thể chọn một điểm trên NFP làm vị trí đặt bằng cách sử dụng một số phương pháp phỏng đoán.

Tương tự, chúng ta có thể xây dựng một "Đa giác vừa vặn bên trong" cho bộ phận và thùng. Điều này giống với NFP, ngoại trừ đa giác quỹ đạo nằm bên trong hình tĩnh.

Khi hai hoặc nhiều bộ phận đã được đặt xong, chúng ta có thể lấy liên kết các NFP của các bộ phận đã đặt trước đó.

# No-Fif Polygon
Điều này có nghĩa là chúng ta cần tính toán các NFP O (nlogn) để hoàn thành việc đóng gói đầu tiên. Trong khi có nhiều cách để giảm thiểu điều này, chúng tôi áp dụng phương pháp brute-force có các đặc tính tốt cho thuật toán tối ưu hóa.

# Đánh giá giá trị tham giá No-Fif polygon
Trong Generic Argothorithm của chúng tôi, thứ tự chèn và sự xoay vòng của các phần tạo thành gen. Chức năng thể dục tuân theo các quy tắc sau:

Giảm thiểu số lượng các bộ phận không thể thay thế được (các bộ phận không thể lắp vừa với bất kỳ thùng nào do sự quay của nó)
Giảm thiểu số lượng thùng được sử dụng
Giảm thiểu chiều rộng của tất cả các bộ phận được đặt
Cái thứ ba là khá tùy ý, vì chúng tôi cũng có thể tối ưu hóa cho các giới hạn hình chữ nhật hoặc một thân tàu lõm tối thiểu. Trong thế giới thực, vật liệu được cắt có xu hướng là hình chữ nhật, và những lựa chọn đó có xu hướng dẫn đến các mảnh dài của vật liệu không được sử dụng.

Vì những đột biến nhỏ trong gen gây ra những thay đổi lớn về thể lực nói chung, các cá thể của quần thể có thể rất giống nhau. Bằng cách lưu vào bộ nhớ đệm NFP, các cá nhân mới có thể được đánh giá rất nhanh chóng.

# Hiệu suất của No-Fif Polygon
Hoạt động tương tự như phần mềm thương mại, sau khi cả hai đã chạy trong khoảng 5 phút.

# Thông số cấu hình
- Khoảng trống giữa các bộ phận: Khoảng trống tối thiểu giữa các bộ phận (ví dụ: đối với laser kerf, bù đắp CNC, v.v.)
- Dung sai đường cong: Sai số tối đa cho phép đối với các đường cung và đường gần đúng tuyến tính của Bezier, tính bằng đơn vị SVG hoặc "pixel". Giảm giá trị này nếu các phần cong có vẻ hơi chồng lên nhau.
- Phần quay: Các khả năng số quay để đánh giá cho từng phần. ví dụ. 4 chỉ cho các hướng cơ bản. Các giá trị lớn hơn có thể cải thiện kết quả, nhưng hội tụ sẽ chậm hơn.
- Quần thể GA: Kích thước quần thể cho Thuật toán Di truyền
- Tỷ lệ đột biến GA: Xác suất đột biến đối với từng vị trí gen hoặc từng phần. Giá trị từ 1-50
- Một phần: Khi được bật, đặt các bộ phận vào các lỗ của các bộ phận khác. Điều này được tắt theo mặc định vì nó có thể tốn nhiều tài nguyên
- Khám phá các khu vực lõm: Khi được bật, giải quyết trường hợp cạnh lõm với chi phí bằng một số hiệu suất và độ chắc chắn của vị trí:
