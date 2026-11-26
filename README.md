# STLab03 · EduParking

Lê Phan Thành Thiên Định · 23110074 · Software Testing

Ứng dụng Python quản lý bãi xe, kiểm thử 12 requirement bằng pytest. Phiên bản v1 có 63 PASS, 7 FAIL trên 70 ca. Bốn bản sửa đưa v2 lên 70 PASS. Cả hai lần đạt 100% line và branch coverage. Sáu mutant độc lập đều bị phát hiện.

## Chạy notebook

Mở [notebook trên Colab](https://colab.research.google.com/github/thiendinh1/STLab03-EduParking/blob/main/23110074_LePhanThanhThienDinh_STLab03.ipynb), chọn **Runtime → Run all** trong phiên mới. Notebook tự tạo các file trong thư mục đang chạy, bắt đầu bằng mã v1 và kết thúc bằng v2. Có thể chạy tương tự từ Jupyter trong thư mục trống.

## Chạy regression tại máy

Dùng Python 3.9 trở lên trong môi trường riêng. Từ thư mục repository chạy:

```sh
python -m pip install pytest pytest-cov pytest-html pandas openpyxl matplotlib
python -m pytest -q test_functions.py test_parking.py --cov=parking_app --cov-branch
```

## Đọc kết quả

- `requirements.json` và `test_data.csv` chứa luật, input, expected và liên kết tên test.
- `parking_app_v1.py` là bản gốc. `parking_app.py` là bản sửa.
- `reports/v1` và `reports/v2` chứa Excel, dashboard, pytest HTML, CSV, XML, log, coverage và biểu đồ. Tải dashboard cùng chart.png để xem hình.
- `reports/mutants.csv` liệt kê mọi test phát hiện từng mutant.
- PDF trình bày defect, phương pháp, kết quả và phần trả lời tự luận.
