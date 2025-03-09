import open3d as o3d

# Load the point cloud
pcd = o3d.io.read_point_cloud("output.ply")

# Check if the point cloud is loaded correctly
if not pcd.has_points():
    print("Error: No points found in the point cloud. Check your PLY file!")
    exit()

# Visualize the point cloud
o3d.visualization.draw_geometries([pcd],
                                  window_name="COLMAP 3D Reconstruction",
                                  zoom=0.5,
                                  front=[0, 0, -1],
                                  lookat=[0, 0, 0],
                                  up=[0, -1, 0])
