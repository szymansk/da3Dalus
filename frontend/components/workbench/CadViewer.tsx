"use client";
// @ts-nocheck — three.js types conflict with Next.js globals

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

interface CadViewerProps {
  /** URL to an STL file to render */
  stlUrl: string | null;
}

/**
 * Renders an STL file using three.js.
 * MVP viewer — will be upgraded to three-cad-viewer later.
 */
export function CadViewer({ stlUrl }: CadViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!containerRef.current || !stlUrl) return;
    const url = stlUrl; // narrow type for closure
    let disposed = false;

    async function loadAndRender() {
      setLoading(true);
      setError(null);

      try {
        const { STLLoader } = await import("three/examples/jsm/loaders/STLLoader.js");
        const { OrbitControls } = await import("three/examples/jsm/controls/OrbitControls.js");

        if (disposed || !containerRef.current) return;

        const container = containerRef.current;
        const w = container.clientWidth;
        const h = container.clientHeight;

        // Cleanup previous renderer
        if (rendererRef.current) {
          rendererRef.current.dispose();
          container.innerHTML = "";
        }

        // Scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x17171a); // --card-muted

        // Camera
        const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 1000);

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Lights
        scene.add(new THREE.AmbientLight(0xffffff, 0.6));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(1, 2, 3);
        scene.add(dirLight);

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;

        // Load STL
        const loader = new STLLoader();
        const response = await globalThis.fetch(url);
        if (!response.ok) throw new Error(`STL fetch failed: ${response.status}`);
        const buffer = await response.arrayBuffer();
        const geometry = loader.parse(buffer);

        if (disposed) return;

        // Material
        const material = new THREE.MeshStandardMaterial({
          color: 0xff8400, // --primary
          metalness: 0.1,
          roughness: 0.6,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        // Auto-fit camera
        geometry.computeBoundingBox();
        const box = geometry.boundingBox!;
        const center = new THREE.Vector3();
        box.getCenter(center);
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);

        camera.position.set(
          center.x + maxDim,
          center.y + maxDim * 0.7,
          center.z + maxDim,
        );
        camera.lookAt(center);
        controls.target.copy(center);
        controls.update();

        // Render loop
        function animate() {
          if (disposed) return;
          requestAnimationFrame(animate);
          controls.update();
          renderer.render(scene, camera);
        }
        animate();

        // Resize handler
        const onResize = () => {
          if (!container || disposed) return;
          const nw = container.clientWidth;
          const nh = container.clientHeight;
          camera.aspect = nw / nh;
          camera.updateProjectionMatrix();
          renderer.setSize(nw, nh);
        };
        window.addEventListener("resize", onResize);

        setLoading(false);

        return () => {
          window.removeEventListener("resize", onResize);
        };
      } catch (err) {
        if (!disposed) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    }

    loadAndRender();

    return () => {
      disposed = true;
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [stlUrl]);

  if (!stlUrl) {
    return null;
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-destructive">
            Viewer Error
          </span>
          <span className="text-[12px] text-muted-foreground">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-card-muted/80">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Loading 3D model…
          </span>
        </div>
      )}
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
