from roboflow import Roboflow
from ultralytics import YOLO
import shutil
import os

def main():
    print("1. Đang tải Dataset từ Roboflow...")
    # Khởi tạo tải data từ API được cung cấp
    rf = Roboflow(api_key="XcDl59T2Ds8HE52p5zUU")
    project = rf.workspace("phongdgos-workspace").project("rock-paper-scissors-sxsw-ouw36")
    version = project.version(1)
    dataset = version.download("yolov8")
    
    print(f"Dataset đã tải xong với vị trí: {dataset.location}")
    print("\n2. Bắt đầu huấn luyện (Train) mô hình AI YOLOv8...")
    print("---- Quá trình này có thể tốn từ 10 - 30 phút tùy tốc độ máy tính ----")
    
    # Sử dụng mô hình nano YOLOv8n nhỏ gọn để train nhanh nhất
    model = YOLO("yolov8n.pt") 
    
    # Bạn có thể tăng số epoch (chu kỳ học) nếu AI chưa nhận diện chuẩn xác. 
    # Mặc định để 20 epoch để test nhanh.
    data_yaml_path = f"{dataset.location}/data.yaml"
    model.train(
        data=data_yaml_path,
        epochs=20,          
        imgsz=640,
        project="yolo_training",
        name="dino_run",
        exist_ok=True, # Ghi đè nếu có lịch sử cũ
        device=0, # Bắt buộc chạy bằng GPU
        workers=0 # SỬA LỖI ĐẦY RAM (WinError 1455): Dùng luồng chính để nạp ảnh
    )

    print("\n3. Hoàn tất quá trình huấn luyện AI!")
    
    # Đường dẫn nơi model YOLO lưu lại file trọng số tốt nhất sau khi chạy xong.
    best_model_path = os.path.join("yolo_training", "dino_run", "weights", "best.pt")
    target_path = "best.pt"
    
    # Kiểm tra xem AI có lưu mô hình thành công không
    if os.path.exists(best_model_path):
        # Di chuyển (copy) file trọng số 'best.pt' ra ngoài thẳng vào thư mục làm việc hiện tại
        shutil.copy(best_model_path, target_path)
        print(f"Thành công! Đã sao chép mô hình đã huấn luyện ra file: {target_path}")
        print("==> BƯỚC TIẾP THEO: Hãy chạy chương trình nhận diện điều khiển game Khủng Long bằng lệnh:")
        print("==> python play_dino.py")
    else:
        print(f"Lỗi: Không tìm thấy trọng số tại đường dẫn mong muốn {best_model_path}.")
        print("Quá trình huấn luyện có thể đã gặp trục trặc (thiếu RAM, thiếu bộ nhớ, vv).")

if __name__ == "__main__":
    main()
