# IPhoneDataCapture
 
App + script to read iphone ARkit position and read and send images over tcp network to python script `CaptureData.py`. They to visualize images and positions of recordings with Qt app.


## To create 3D point cloud from 2D images (advised to run in collab for CUDA and max speed)
### Create 3d point cloud with SfM pipeline (colmap)
- Install colmap (macOs): `brew install colmap`
- export trajectory and images for colmap (with button) (4 hz, total 52 images)
- run feature extraction (colmap): `colmap feature_extractor --database_path database.db --image_path colmap_export/images --ImageReader.camera_model PINHOLE` (3 sec)
- run feature matching: `colmap exhaustive_matcher --database_path database.db ` (50 sec)
- copy camera.txt and images.txt to colmap as prior: 
```bash
mkdir -p colmap_export/sparse/0
cp colmap_export/sparse/cameras.txt colmap_export/sparse/0/ 
cp colmap_export/sparse/images.txt colmap_export/sparse/0/`
```
- run colmap 3d reconstruction: `colmap mapper --database_path database.db --image_path colmap_export/images --output_path colmap_export/sparse --Mapper.init_image_id1 1` (1 min 40 sec)
- visualize running: `colmap gui`, press `File -> Import Model -> (select "sparse/0" folder)`

### Export to ply, visualize with open3D
- export to ply format (for gaussan splatting): `colmap model_converter --input_path colmap_export/sparse/0 --output_path output.ply --output_type PLY`
- Visualize again with open3d: `python visualize_colmap.py`

