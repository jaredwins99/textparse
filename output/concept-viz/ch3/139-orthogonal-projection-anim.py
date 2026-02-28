"""
Orthogonal Projection Animation — Manim
Shows y dropping onto the column space, residual perpendicular to the plane.

Render: manim -qh 139-orthogonal-projection-anim.py OrthogonalProjection
"""
from manim import *
import numpy as np

class OrthogonalProjection(ThreeDScene):
    def construct(self):
        # Dark theme
        self.camera.background_color = "#0d1117"

        # Setup axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-1, 4, 1],
            x_length=6, y_length=6, z_length=5,
            axis_config={"color": "#8b949e", "stroke_width": 1}
        )

        # Column space = xz-plane (y=0 plane, but we use z as "up")
        plane = Surface(
            lambda u, v: axes.c2p(u, v, 0),
            u_range=[-2.5, 2.5], v_range=[-2.5, 2.5],
            resolution=(1, 1),
            fill_color="#bc8cff", fill_opacity=0.15,
            stroke_color="#bc8cff", stroke_width=1, stroke_opacity=0.3
        )

        # Basis vectors for column space
        e1 = Arrow3D(
            start=axes.c2p(0, 0, 0), end=axes.c2p(2, 0, 0),
            color="#39d2c0", thickness=0.03
        )
        e2 = Arrow3D(
            start=axes.c2p(0, 0, 0), end=axes.c2p(0, 2, 0),
            color="#39d2c0", thickness=0.03
        )

        # y vector (above the plane)
        y_point = np.array([1.5, 1.0, 3.0])
        y_hat_point = np.array([1.5, 1.0, 0.0])  # projection onto plane

        y_arrow = Arrow3D(
            start=axes.c2p(0, 0, 0), end=axes.c2p(*y_point),
            color="#f778ba", thickness=0.04
        )

        # Labels
        plane_label = Text("Column Space of X", font_size=24, color="#bc8cff")
        y_label = Text("y", font_size=28, color="#f778ba", weight=BOLD)
        yhat_label = Text("ŷ = Hy", font_size=24, color="#3fb950", weight=BOLD)
        e_label = Text("e = y - ŷ", font_size=24, color="#d29922", weight=BOLD)
        perp_label = Text("⊥", font_size=32, color="#d29922", weight=BOLD)

        # Set initial camera
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)

        # ── Phase 0: Setup ──
        self.play(FadeIn(axes), run_time=0.5)
        self.play(FadeIn(plane), run_time=1)

        self.add_fixed_orientation_mobjects(plane_label)
        plane_label.move_to(axes.c2p(2.5, -2.5, 0.3))
        self.play(Write(plane_label), run_time=0.8)

        self.play(Create(e1), Create(e2), run_time=1)
        self.play(Create(y_arrow), run_time=1)

        self.add_fixed_orientation_mobjects(y_label)
        y_label.move_to(axes.c2p(*(y_point + np.array([0.3, 0, 0.3]))))
        self.play(Write(y_label), run_time=0.5)

        self.wait(0.5)

        # ── Phase 1: Drop ──
        # Animate a dot falling from y to yhat
        drop_dot = Dot3D(point=axes.c2p(*y_point), color="#f778ba", radius=0.08)
        self.play(FadeIn(drop_dot), run_time=0.3)

        # Dashed trail
        trail = DashedLine(
            start=axes.c2p(*y_point), end=axes.c2p(*y_hat_point),
            color="#8b949e", dash_length=0.1
        )

        self.play(
            drop_dot.animate.move_to(axes.c2p(*y_hat_point)),
            Create(trail),
            run_time=2,
            rate_func=rate_functions.ease_in_quad
        )

        # ── Phase 2: Land ──
        yhat_dot = Dot3D(point=axes.c2p(*y_hat_point), color="#3fb950", radius=0.1)
        self.play(
            FadeIn(yhat_dot, scale=1.5),
            FadeOut(drop_dot),
            run_time=0.8
        )

        self.add_fixed_orientation_mobjects(yhat_label)
        yhat_label.move_to(axes.c2p(*(y_hat_point + np.array([0.8, 0, -0.3]))))
        self.play(Write(yhat_label), run_time=0.6)

        # Right angle marker
        marker_size = 0.3
        corner = axes.c2p(*y_hat_point)
        up = axes.c2p(*(y_hat_point + np.array([0, 0, marker_size])))
        side = axes.c2p(*(y_hat_point + np.array([marker_size, 0, 0])))
        diag = axes.c2p(*(y_hat_point + np.array([marker_size, 0, marker_size])))

        right_angle = VGroup(
            Line3D(start=up, end=diag, color="#d29922", thickness=0.02),
            Line3D(start=side, end=diag, color="#d29922", thickness=0.02),
        )
        self.play(Create(right_angle), run_time=0.5)

        # ── Phase 3: Residual ──
        residual_arrow = Arrow3D(
            start=axes.c2p(*y_hat_point), end=axes.c2p(*y_point),
            color="#d29922", thickness=0.04
        )

        self.play(
            FadeOut(trail),
            Create(residual_arrow),
            run_time=1.5
        )

        self.add_fixed_orientation_mobjects(e_label)
        e_label.move_to(axes.c2p(*(0.5 * (y_point + y_hat_point) + np.array([0.8, 0, 0]))))
        self.play(Write(e_label), run_time=0.6)

        self.add_fixed_orientation_mobjects(perp_label)
        perp_label.move_to(axes.c2p(*(y_hat_point + np.array([-0.5, 0, 0.5]))))
        self.play(Write(perp_label), run_time=0.5)

        self.wait(1)

        # ── Phase 4: Rotate to show perpendicularity ──
        self.begin_ambient_camera_rotation(rate=0.4)
        self.wait(8)
        self.stop_ambient_camera_rotation()

        # Final formula
        formula = MathTex(
            r"\hat{y} = Hy = X(X^TX)^{-1}X^Ty",
            font_size=36, color="#e6edf3"
        )
        self.add_fixed_in_frame_mobjects(formula)
        formula.to_edge(DOWN, buff=0.5)
        self.play(Write(formula), run_time=1.5)

        self.wait(2)
