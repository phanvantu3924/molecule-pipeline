Tổng quan hệ thống

Pipeline hoạt động theo vòng lặp đơn giản:

Khởi tạo kế hoạch chạy (số vòng, số phân tử mỗi vòng, ràng buộc).

Sinh phân tử ứng viên từ các SMILES seed ban đầu.

Tính toán các thuộc tính hóa học bằng RDKit.

Áp dụng các luật sàng lọc.

Chấm điểm và xếp hạng các phân tử đạt yêu cầu.

Lấy các phân tử tốt nhất làm seed cho vòng tiếp theo.

Toàn bộ quá trình được chạy bất đồng bộ và có lưu lại dấu vết thực thi.

Các vai trò (Agent)

Hệ thống được tổ chức theo ba vai trò logic rõ ràng:

Planner
Chịu trách nhiệm khởi tạo chiến lược chạy: số vòng, số ứng viên mỗi vòng và các ràng buộc sàng lọc.
Planner được cài đặt theo cách xác định (deterministic), đóng vai trò gom và thể hiện “ý định” của một lượt chạy.

Generator
Sinh ra các phân tử ứng viên bằng cách biến đổi các SMILES seed.
Các phép biến đổi mang tính heuristic (ví dụ: đổi halogen, thêm hoặc bớt fragment đơn giản).
Các SMILES sinh ra được kiểm tra hợp lệ và loại trùng.

Ranker
Chấm điểm các phân tử vượt qua sàng lọc và chọn ra các ứng viên tốt nhất.
Các phân tử này được dùng làm seed cho vòng tiếp theo.

Ba vai trò này được tách rõ trong code để thể hiện vòng lặp agentic một cách minh bạch.

Công cụ hóa học

RDKit được sử dụng cho toàn bộ các thao tác hóa học, bao gồm:

Kiểm tra tính hợp lệ của SMILES

Tính toán các thuộc tính:

Khối lượng phân tử (MW)

LogP

Số nhóm cho liên kết hydro (HBD)

Số nhóm nhận liên kết hydro (HBA)

Diện tích bề mặt phân cực (TPSA)

Số liên kết xoay được

QED

Sàng lọc và chấm điểm

Các phân tử được sàng lọc dựa trên các luật đơn giản, lấy cảm hứng từ Lipinski và TPSA, cho phép tối đa một số lượng vi phạm nhất định.

Các phân tử vượt qua sàng lọc được chấm điểm theo công thức:

score = QED − 0.1 × số lượng vi phạm

Sau đó các phân tử được xếp hạng theo điểm số này.

Truy vết (Trace)

Hệ thống lưu lại dấu vết thực thi dưới dạng có cấu trúc, bao gồm:

Quyết định của Planner (tham số và ràng buộc của lượt chạy)

Hoạt động sinh phân tử của Generator theo từng vòng

Quyết định chọn seed của Ranker

Dữ liệu trace có thể truy vấn qua API, phục vụ cho việc kiểm tra, debug và tái lập quá trình chạy.

API

POST /runs
Khởi tạo một lượt chạy mới.
Lượt chạy được thực thi bất đồng bộ, không chặn request.

GET /runs/{run_id}/trace
Lấy thông tin trace của một lượt chạy.

GET /
Endpoint kiểm tra nhanh trạng thái service.

Cài đặt và chạy

Tạo môi trường ảo:

python -m venv venv
source venv/bin/activate

Cài đặt thư viện:

pip install -r requirements.txt

Lưu ý về RDKit:
RDKit có thể không cài được ổn định bằng pip trên một số hệ thống.
Khuyến nghị cài bằng conda:

conda install -c conda-forge rdkit

Chạy server:

uvicorn main:app --reload

Server chạy tại: http://localhost:8000

Ví dụ sử dụng

Khởi chạy một lượt:

curl -X POST http://localhost:8000/runs

-H "Content-Type: application/json"
-d '{
"seed_smiles": ["CC(=O)Oc1ccccc1C(=O)O", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"],
"rounds": 3,
"candidates_per_round": 30,
"top_k": 10
}'

Lấy trace:

curl http://localhost:8000/runs/{run_id}/trace

Ghi chú thiết kế

Phần cài đặt này được giữ ở mức đơn giản và xác định.

Mục tiêu chính là thể hiện cấu trúc hệ thống, vòng lặp agentic, khả năng truy vết và tích hợp công cụ khoa học, thay vì tối ưu thuật toán hóa học.

Các agent được cài đặt dưới dạng module logic, không sử dụng LLM.
SQLite và FastAPI BackgroundTasks được dùng để đơn giản hóa việc demo.
