Bản tối ưu phản hồi nhanh cho Chrome Dino
=========================================

Những gì đã chỉnh:
- Giảm độ trễ camera bằng cách đặt buffer thấp và ưu tiên MJPG.
- Chỉ suy luận trong vùng giữa khung hình (ROI) để tăng tốc và giảm nhiễu.
- Giảm kích thước suy luận xuống 416 để tăng FPS.
- Chỉ lấy detection mạnh nhất (max_det=1).
- Dùng cơ chế tích lũy điểm theo confidence thay vì chờ cứng nhiều frame.
- Nếu confidence đủ cao sẽ phản ứng gần như tức thì.
- Paper: nhảy theo rising edge, tránh spam vô hạn nhưng vẫn rất nhanh.
- Rock: giữ cúi đúng theo trạng thái tay.
- Scissors: cancel / neutral.
- Overlay có FPS và loop latency để debug.

Cách chạy:
1. pip install -r requirements.txt
2. Mở game Chrome Dino và click vào cửa sổ game.
3. python play_dino.py
4. Đặt tay trong khung ROI màu xanh để ổn định và nhanh hơn.

Lưu ý thực tế:
- Không thể nhanh tuyệt đối như bàn phím thật vì còn độ trễ webcam + mô hình.
- Nhưng bản này giảm đáng kể độ trễ cảm nhận so với kiểu suy luận cả khung hình và chờ ổn định nhiều frame.
