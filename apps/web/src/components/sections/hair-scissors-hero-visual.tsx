'use client';

import { ContactShadows, Environment, Float, OrbitControls, useGLTF } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import Image from 'next/image';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Box3, type Group, type Mesh, type MeshStandardMaterial, Vector3 } from 'three';

const MODEL_PATH = '/models/barbers-scissors.glb';

function BarbersScissorsModel() {
  const modelRef = useRef<Group>(null);
  const gltf = useGLTF(MODEL_PATH);
  const scene = useMemo(() => gltf.scene.clone(), [gltf.scene]);

  useEffect(() => {
    scene.traverse((child) => {
      const mesh = child as Mesh;

      if (mesh.isMesh) {
        mesh.castShadow = true;
        mesh.receiveShadow = true;

        if (mesh.material) {
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of materials) {
            const material = mat as MeshStandardMaterial;
            if ('metalness' in material && 'roughness' in material) {
              material.metalness = 0.95;
              material.roughness = 0.18;
              if ('color' in material) {
                material.color.set('#dcdcdc');
              }
            }
          }
        }
      }
    });

    // Reset scale and position to base values before calculating bounding box
    scene.scale.set(1, 1, 1);
    scene.position.set(0, 0, 0);

    // Center pivot point
    const box = new Box3().setFromObject(scene);
    const center = new Vector3();
    box.getCenter(center);

    scene.position.x = -center.x;
    scene.position.y = -center.y;
    scene.position.z = -center.z;

    // Auto-normalize scale to be larger
    const size = new Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    if (maxDim > 0) {
      const targetSize = 1.99; // Larger target size to fill space better
      const scaleFactor = targetSize / maxDim;
      scene.scale.set(scaleFactor, scaleFactor, scaleFactor);
    }
  }, [scene]);

  useFrame((_, delta) => {
    if (!modelRef.current) {
      return;
    }

    modelRef.current.rotation.y += delta * 0.22;
  });

  return (
    <Float floatIntensity={1.1} rotationIntensity={0.4} speed={1.3}>
      <group ref={modelRef} rotation={[0.2, -0.6, -0.1]} position={[0, -0.1, 0]}>
        <primitive object={scene} />
      </group>
    </Float>
  );
}

function SceneContent() {
  return (
    <>
      <ambientLight intensity={0.25} />
      <directionalLight castShadow intensity={2.6} position={[3, 5, 5]} />
      <spotLight angle={0.4} intensity={1.5} penumbra={0.7} position={[-4, 5, 3]} />
      <Suspense fallback={null}>
        <BarbersScissorsModel />
        <Environment preset="studio" />
        <ContactShadows blur={2.2} far={5} opacity={0.26} position={[0, -1.7, 0]} scale={5} />
      </Suspense>
      <OrbitControls
        autoRotate={false}
        enablePan={false}
        enableZoom={false}
        maxPolarAngle={Math.PI / 1.85}
        minPolarAngle={Math.PI / 3.4}
      />
    </>
  );
}

export function HairScissorsHeroVisual() {
  const [webGLSupported, setWebGLSupported] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const isSupported = !!(
        window.WebGLRenderingContext &&
        (canvas.getContext('webgl2') ||
          canvas.getContext('webgl') ||
          canvas.getContext('experimental-webgl'))
      );
      setWebGLSupported(isSupported);
    } catch (e) {
      setWebGLSupported(false);
    }
  }, []);

  if (webGLSupported === null) {
    // Prevent flash of content during mount check
    return <div className="w-full h-[400px] sm:h-[450px] md:h-[500px]" />;
  }

  if (webGLSupported === false) {
    return (
      <div className="w-full h-[400px] sm:h-[450px] md:h-[500px] flex items-center justify-center relative overflow-hidden bg-gradient-to-tr from-[#faf6f0] to-[#f5ebd6] rounded-[2rem] p-6 border border-white/20 shadow-[0_20px_50px_rgba(136,14,79,0.04)]">
        <div className="absolute inset-0 bg-white/30 backdrop-blur-sm pointer-events-none" />
        <div className="relative w-[85%] h-[85%] flex items-center justify-center">
          <Image
            src="/images/hero/salon-hero.svg"
            alt="TIEN SALON Haircut"
            fill
            className="object-contain filter drop-shadow-[0_12px_24px_rgba(136,14,79,0.08)]"
            priority
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className="w-full h-[400px] sm:h-[450px] md:h-[500px] relative"
      aria-label="Visual 3D gunting rambut TIEN SALON"
    >
      <Canvas camera={{ fov: 34, position: [0, 0, 4.0] }} dpr={[1, 1.8]} shadows>
        <SceneContent />
      </Canvas>
    </div>
  );
}
