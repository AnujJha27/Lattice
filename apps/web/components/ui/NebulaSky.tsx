"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * NebulaSky — one WebGL shader: drifting fbm nebula clouds in ink/brass,
 * a parallax star layer with twinkle, and a vignette. Single draw surface,
 * GPU-composited: no CSS repaint flicker. Pauses under reduced motion.
 */

const NEBULA_FRAGMENT = /* glsl */ `
precision highp float;
uniform float uTime;
uniform vec2 uResolution;
uniform vec2 uMouse;
uniform float uReducedMotion;

// Hash + value noise + 5-octave fbm
float hash(vec2 p) {
  p = fract(p * vec2(234.34, 435.345));
  p += dot(p, p + 34.23);
  return fract(p.x * p.y);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p) {
  float v = 0.0;
  float amp = 0.55;
  for (int i = 0; i < 5; i++) {
    v += amp * noise(p);
    p *= 2.03;
    amp *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution.xy;
  vec2 p = uv;
  p.x *= uResolution.x / uResolution.y;

  float t = uReducedMotion > 0.5 ? 10.0 : uTime * 0.03;
  vec2 drift = uReducedMotion > 0.5 ? vec2(0.0) : uMouse * 0.06;

  // Layered nebula clouds
  float n1 = fbm(p * 1.6 + vec2(t * 0.5, -t * 0.2) + drift);
  float n2 = fbm(p * 3.1 + vec2(-t * 0.3, t * 0.4) + n1 * 1.5 + drift * 1.6);
  float clouds = smoothstep(0.35, 0.95, n1 * 0.65 + n2 * 0.5);

  // Palette: ink base, indigo clouds, brass highlights
  vec3 ink = vec3(0.039, 0.055, 0.102);        // #0A0E1A
  vec3 indigo = vec3(0.13, 0.18, 0.32);
  vec3 brass = vec3(0.788, 0.663, 0.38);       // #C9A961

  vec3 col = ink;
  col = mix(col, indigo, clouds * 0.55);

  // Brass filaments where cloud density peaks
  float filaments = smoothstep(0.62, 0.9, n2) * clouds;
  col += brass * filaments * 0.22;

  // Deep-space vignette
  float vignette = smoothstep(1.25, 0.35, length(uv - 0.5));
  col *= mix(0.75, 1.0, vignette);

  gl_FragColor = vec4(col, 1.0);
}
`;

const STAR_VERTEX = /* glsl */ `
attribute float aSize;
attribute float aPhase;
attribute float aWarm;
uniform float uTime;
uniform float uPixelRatio;
uniform float uReducedMotion;
varying float vAlpha;
varying float vWarm;
void main() {
  vWarm = aWarm;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  float twinkle = mix(0.55, 1.0, 0.5 + 0.5 * sin(uTime * (0.4 + aPhase * 0.7) + aPhase * 40.0));
  if (uReducedMotion > 0.5) twinkle = 0.8;
  vAlpha = twinkle;
  gl_PointSize = aSize * uPixelRatio * twinkle;
  gl_Position = projectionMatrix * mv;
}
`;

const STAR_FRAGMENT = /* glsl */ `
precision highp float;
varying float vAlpha;
varying float vWarm;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float soft = smoothstep(0.5, 0.05, d);
  vec3 white = vec3(0.92, 0.90, 0.85);
  vec3 brass = vec3(0.79, 0.66, 0.38);
  vec3 col = mix(white, brass, vWarm);
  gl_FragColor = vec4(col, soft * vAlpha * 0.9);
}
`;

function Nebula() {
  const { viewport } = useThree();
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const mouse = useRef(new THREE.Vector2(0, 0));
  const target = useRef(new THREE.Vector2(0, 0));

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2(1, 1) },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uReducedMotion: { value: 0 },
    }),
    [],
  );

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    uniforms.uReducedMotion.value = reduced ? 1 : 0;
    const onMove = (e: PointerEvent) => {
      target.current.set(
        (e.clientX / window.innerWidth) * 2 - 1,
        (e.clientY / window.innerHeight) * 2 - 1,
      );
    };
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, [uniforms]);

  useFrame((state, delta) => {
    uniforms.uTime.value += delta;
    uniforms.uResolution.value.set(
      state.size.width * state.viewport.dpr,
      state.size.height * state.viewport.dpr,
    );
    // Ease mouse for slow, heavy parallax
    mouse.current.lerp(target.current, 0.02);
    uniforms.uMouse.value.copy(mouse.current);
    if (materialRef.current) {
      materialRef.current.uniforms.uTime = uniforms.uTime;
      materialRef.current.uniforms.uResolution = uniforms.uResolution;
      materialRef.current.uniforms.uMouse = uniforms.uMouse;
      materialRef.current.uniforms.uReducedMotion = uniforms.uReducedMotion;
    }
  });

  return (
    <mesh scale={[viewport.width, viewport.height, 1]}>
      <planeGeometry args={[1, 1]} />
      <shaderMaterial
        ref={materialRef}
        fragmentShader={NEBULA_FRAGMENT}
        vertexShader={/* glsl */ `
          void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
        `}
        uniforms={uniforms}
        depthWrite={false}
      />
    </mesh>
  );
}

function Stars({ count = 700 }: { count?: number }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPixelRatio: { value: 1 },
      uReducedMotion: { value: 0 },
    }),
    [],
  );

  const { positions, sizes, phases, warms } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const phases = new Float32Array(count);
    const warms = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 22;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 2] = -Math.random() * 8 - 1; // depth for parallax
      sizes[i] = Math.random() * 3 + 0.6;
      phases[i] = Math.random();
      warms[i] = Math.random() < 0.14 ? 1 : 0;
    }
    return { positions, sizes, phases, warms };
  }, [count]);

  useEffect(() => {
    uniforms.uPixelRatio.value = Math.min(window.devicePixelRatio, 2);
    uniforms.uReducedMotion.value = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches
      ? 1
      : 0;
  }, [uniforms]);

  useFrame((_, delta) => {
    uniforms.uTime.value += delta;
    if (materialRef.current) {
      materialRef.current.uniforms.uTime = uniforms.uTime;
    }
  });

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-aSize" args={[sizes, 1]} />
        <bufferAttribute attach="attributes-aPhase" args={[phases, 1]} />
        <bufferAttribute attach="attributes-aWarm" args={[warms, 1]} />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        vertexShader={STAR_VERTEX}
        fragmentShader={STAR_FRAGMENT}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function NebulaSky({ starCount = 700, fixed = false }: { starCount?: number; fixed?: boolean }) {
  return (
    <div aria-hidden className={`pointer-events-none ${fixed ? "fixed" : "absolute"} inset-0`}>
      <Canvas
        dpr={[1, 1.5]}
        gl={{ antialias: false, powerPreference: "high-performance" }}
        camera={{ position: [0, 0, 5], fov: 60 }}
        style={{ position: "absolute", inset: 0 }}
      >
        <Nebula />
        <Stars count={starCount} />
      </Canvas>
    </div>
  );
}
