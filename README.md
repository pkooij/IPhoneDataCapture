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

### Create 3d point cloud with MVS pipeline (colmap)
- `colmap image_undistorter --image_path colmap_export/images --input_path colmap_export/sparse/0 --output_path colmap_export/dense --output_type COLMAP`

TODO:
- Implement this with colmap (MVS), run in collab

### Export to ply, visualize and create Gaussian splat (or use directly ply input from realsense)
- export to ply format (for gaussan splatting): `colmap model_converter --input_path colmap_export/sparse/0 --output_path output.ply --output_type PLY`
- Visualize again with open3d: `python visualize_colmap.py`

- Clone (`https://github.com/j-alex-hanson/speedy-splat`) or go in the 'speedy-splat' folder and run: `python convert.py --source_path ../IPhoneDataCapture/colmap_export/ --camera PINHOLE --skip_matching`

TODO:
- use DISK and lightglue and compare with current colmpa only approach

- Implement splatting (test in collab)! `https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/`

### Export to ply, visualize and create Phtogrammy 3d with OpenMVS
- export to ply format (for gaussan splatting): `colmap model_converter --input_path colmap_export/sparse/0 --output_path output.ply --output_type PLY`
- Visualize again with open3d: `python visualize_colmap.py`

