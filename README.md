# IPhoneDataCapture
 
App + script to read iphone ARkit position and read and send images over tcp network to python script `CaptureData.py`. They to visualize images and positions of recordings with Qt app.


## To create 3D point cloud from 2D images
### Create 3d point cloud with sft pipeline (colmap)
- Install colmap (macOs): `brew install colmap`
- export trajectory and images for colmap (with button) (4 sec trajectory)
- run feature extraction (colmap): `colmap feature_extractor --database_path database.db --image_path colmap_export/images --ImageReader.camera_model PINHOLE` (15 sec)
- run feature matching: `colmap exhaustive_matcher --database_path database.db ` (30 min)
- copy camera.txt and images.txt to colmap as prior: 
```bash
mkdir -p colmap_export/sparse/0
cp colmap_export/sparse/cameras.txt colmap_export/sparse/0/ 
cp colmap_export/sparse/images.txt colmap_export/sparse/0/`
```
- run colmap 3d reconstruction: `colmap mapper --database_path database.db --image_path colmap_export/images --output_path colmap_export/sparse --Mapper.init_image_id1 1` (18 min)

### Export to ply, visualize and create Gaussian splat (or use directly ply input from realsense)
- export to ply format (for gaussan splatting): `colmap model_converter --input_path colmap_export/sparse/0 --output_path output.ply --output_type PLY`
- Visualize again with open3d: `python visualize_colmap.py`


- Todo
- use lightglue / (super gleu)
- with DISK (or superpoint)

### Export to ply, visualize and create Phtogrammy 3d with OpenMVS
- export to ply format (for gaussan splatting): `colmap model_converter --input_path colmap_export/sparse/0 --output_path output.ply --output_type PLY`
- Visualize again with open3d: `python visualize_colmap.py`