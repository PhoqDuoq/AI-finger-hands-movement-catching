Dino hand control - bản đã vá

File gồm:
- play_dino.py
- best.pt
- requirements.txt

Cách chạy:
1. pip install -r requirements.txt
2. Mở Chrome Dino và click vào cửa sổ game
3. python play_dino.py

Đã sửa:
- Chỉ lấy detection tốt nhất
- Lọc box nhỏ gây nhiễu
- Ổn định cử chỉ theo nhiều frame
- Paper = jump có cooldown
- Rock = duck theo trạng thái thật
- Tự nhả phím down khi mất cử chỉ hoặc thoát
