import math

from taichi.dynamics.mpm import MPM3
from taichi.core import tc_core
from taichi.misc.util import Vector
from taichi.visual import *
from taichi.visual.post_process import *
from taichi.visual.texture import Texture
from colorsys import hsv_to_rgb
import taichi as tc

gi_render = True
step_number = 400
# step_number = 1
# total_frames = 1
grid_downsample = 2
output_downsample = 2
render_epoch = 50


def create_mpm_sand_block(fn):
    particles = tc_core.RenderParticles()
    assert particles.read(fn)
    downsample = grid_downsample
    tex = Texture.from_render_particles((255 / downsample, 255 / downsample, 255 / downsample), particles) * 5
    # tex = Texture('sphere', center=(0.5, 0.5, 0.5), radius=0.5)
    with tc.transform_scope(scale=2):
        return tc.create_volumetric_block(tex, res=(128, 128, 128))


def create_scene(frame, d, t):
    downsample = output_downsample
    width, height = 1280 / downsample, 720 / downsample

    camera = Camera('pinhole', width=width, height=height, fov=25,
                    origin=(0, 0, 8), look_at=(0, 0, 0), up=(0, 1, 0))
    # camera = Camera('pinhole', width=width, height=height, fov=30,
    #                 origin=(2, 4, 4), look_at=(0, 0, 0), up=(0, 1, 0))

    scene = Scene()
    with scene:
        scene.set_camera(camera)

        with tc.transform_scope(rotation=(20, 0, 0), translate=(0, 0, 0), scale=1):
            with tc.transform_scope(rotation=(0, -20, 0), translate=(0, 0.7, 0), scale=1):
                mesh = tc.Mesh('plane', tc.SurfaceMaterial('emissive', color=(30000, 40000, 60000)),
                               translate=(-20, 30, 0), scale=3, rotation=(0, 0, 180))
                scene.add_mesh(mesh)
                mesh = tc.Mesh('plane', tc.SurfaceMaterial('emissive', color=(6000, 8000, 12000)),
                               translate=(20, 30, 40), scale=3, rotation=(0, 0, -180))
                scene.add_mesh(mesh)

                material = SurfaceMaterial('diffuse', color=(0.24, 0.18, 0.12), f0=1)
                scene.add_mesh(Mesh('cube', material=material, translate=(0, -1, 0), scale=(1.25, 0.02, 0.8)))

                fn = d + r'/particles%05d.bin' % frame
                mesh = create_mpm_sand_block(fn)
                scene.add_mesh(mesh)

        envmap_texture = Texture('spherical_gradient', inside_val=(10, 10, 10, 10), outside_val=(1, 1, 1, 0),
                                 angle=10, sharpness=20)
        envmap = EnvironmentMap('base', texture=envmap_texture.id, res=(1024, 1024))
        scene.set_environment_map(envmap)

    return scene


def render_frame(frame, d, t):
    renderer = Renderer(output_dir='volumetric', overwrite=True, frame=frame)
    renderer.initialize(preset='pt', scene=create_scene(frame, d, t), sampler='prand', max_path_length=3)
    renderer.set_post_processor(LDRDisplay(exposure=1, bloom_radius=0.00, bloom_threshold=1.0))
    renderer.render(render_epoch)


if __name__ == '__main__':
    downsample = grid_downsample
    resolution = (255 / downsample, 255 / downsample, 255 / downsample)

    mpm = MPM3(resolution=resolution, gravity=(0, -10, 0), async=True, num_threads=8, strength_dt_mul=4,
               affine_damping=1000)

    # real theta_c = 2.5e-2f, theta_s = 7.5e-3f;

    tex_ball1 = Texture('sphere', center=(0.41, 0.23, 0.5), radius=0.08) * 1
    tex_ball1 = tex_ball1 * (Texture('perlin') * 6 + 2)
    mpm.add_particles(density_tex=tex_ball1.id, initial_velocity=(200, 5, 0), compression=1.0,
                      mu_0=3e5, lambda_0=3e5)

    tex_ball2 = Texture('sphere', center=(0.59, 0.2, 0.5), radius=0.08) * 1
    tex_ball2 = tex_ball2 * (Texture('perlin') * 6 + 2)
    mpm.add_particles(density_tex=tex_ball2.id, initial_velocity=(-200, 5, 0), compression=1.0,
                      mu_0=3e5, lambda_0=3e5)

    levelset = mpm.create_levelset()
    levelset.add_cuboid((0.01, 0.01, 0.01), (0.99, 0.99, 0.99), True)
    mpm.set_levelset(levelset)

    t = 0
    for i in range(step_number):
        print 'process(%d/%d)' % (i, step_number)
        mpm.step(0.01)
        t += 0.01
        if gi_render:
            d = mpm.get_directory()
            if i % 10 == 0:
                render_frame(i, d, t)
                pass
    mpm.make_video()
