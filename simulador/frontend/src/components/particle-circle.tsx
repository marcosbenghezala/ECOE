import { useEffect, useRef, useCallback } from "react"
import * as THREE from "three"

interface ParticleCircleProps {
  speaker: "idle" | "user" | "agent"
  audioLevel: number
  className?: string
}

export function ParticleCircle({ speaker, audioLevel, className }: ParticleCircleProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null)
  const particlesRef = useRef<THREE.Points | null>(null)
  const frameRef = useRef<number>(0)

  // idle: gris muy oscuro, user (escucha): gris oscuro, agent (habla): rojo intenso
  // UMH siempre en rojo oscuro
  const targetColorsRef = useRef<{
    circle: { r: number; g: number; b: number }
    text: { r: number; g: number; b: number }
  }>({
    circle: { r: 0.15, g: 0.15, b: 0.15 }, // Gris muy oscuro por defecto
    text: { r: 0.6, g: 0.0, b: 0.0 }, // Rojo oscuro para UMH
  })

  const currentColorsRef = useRef<{
    circle: { r: number; g: number; b: number }
    text: { r: number; g: number; b: number }
  }>({
    circle: { r: 0.15, g: 0.15, b: 0.15 },
    text: { r: 0.6, g: 0.0, b: 0.0 },
  })

  const smoothedAudioRef = useRef(0)
  const basePositionsRef = useRef<Float32Array | null>(null)
  const isTextParticleRef = useRef<boolean[]>([])
  const textScaleRef = useRef(1)
  const targetTextScaleRef = useRef(1)

  const generateTextPositions = useCallback(() => {
    const canvas = document.createElement("canvas")
    canvas.width = 200
    canvas.height = 200
    const ctx = canvas.getContext("2d")
    if (!ctx) return []

    ctx.fillStyle = "black"
    ctx.fillRect(0, 0, 200, 200)
    ctx.fillStyle = "white"
    ctx.font = "bold 52px Arial"
    ctx.textAlign = "center"
    ctx.textBaseline = "middle"
    ctx.fillText("UMH", 100, 100)

    const imageData = ctx.getImageData(0, 0, 200, 200)
    const positions: { x: number; y: number }[] = []

    for (let y = 0; y < 200; y += 2) {
      for (let x = 0; x < 200; x += 2) {
        const i = (y * 200 + x) * 4
        if (imageData.data[i] > 128) {
          const nx = ((x - 100) / 100) * 0.38
          const ny = ((100 - y) / 100) * 0.38
          positions.push({ x: nx, y: ny })
        }
      }
    }

    return positions
  }, [])

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const width = 400
    const height = 400

    const scene = new THREE.Scene()
    sceneRef.current = scene

    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10)
    camera.position.z = 2
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const textPositions = generateTextPositions()
    const textParticleCount = Math.floor(12000 * 0.15)
    const circleParticleCount = 12000 - textParticleCount

    const totalParticles = 12000
    const positions = new Float32Array(totalParticles * 3)
    const colors = new Float32Array(totalParticles * 3)
    const basePositions = new Float32Array(totalParticles * 3)
    const isTextParticle: boolean[] = []

    const maxRadius = 0.765

    for (let i = 0; i < circleParticleCount; i++) {
      const angle = Math.random() * Math.PI * 2
      const radius = Math.sqrt(Math.random()) * maxRadius
      const x = Math.cos(angle) * radius
      const y = Math.sin(angle) * radius

      positions[i * 3] = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = 0

      basePositions[i * 3] = x
      basePositions[i * 3 + 1] = y
      basePositions[i * 3 + 2] = 0

      colors[i * 3] = 0.15
      colors[i * 3 + 1] = 0.15
      colors[i * 3 + 2] = 0.15

      isTextParticle.push(false)
    }

    const textSampleStep = Math.max(1, Math.floor(textPositions.length / textParticleCount))
    for (let i = 0; i < textParticleCount; i++) {
      const idx = circleParticleCount + i
      const textIdx = (i * textSampleStep) % textPositions.length
      const pos = textPositions[textIdx] || { x: 0, y: 0 }

      const jitter = 0.008
      const x = pos.x + (Math.random() - 0.5) * jitter
      const y = pos.y + (Math.random() - 0.5) * jitter

      positions[idx * 3] = x
      positions[idx * 3 + 1] = y
      positions[idx * 3 + 2] = 0.01

      basePositions[idx * 3] = x
      basePositions[idx * 3 + 1] = y
      basePositions[idx * 3 + 2] = 0.01

      colors[idx * 3] = 0.6
      colors[idx * 3 + 1] = 0.0
      colors[idx * 3 + 2] = 0.0

      isTextParticle.push(true)
    }

    basePositionsRef.current = basePositions
    isTextParticleRef.current = isTextParticle

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3))

    const material = new THREE.PointsMaterial({
      size: 0.028,
      vertexColors: true,
      transparent: true,
      opacity: 1,
      sizeAttenuation: true,
    })

    const particles = new THREE.Points(geometry, material)
    scene.add(particles)
    particlesRef.current = particles

    return () => {
      cancelAnimationFrame(frameRef.current)
      renderer.dispose()
      geometry.dispose()
      material.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [generateTextPositions])

  useEffect(() => {
    switch (speaker) {
      case "idle":
        targetColorsRef.current = {
          circle: { r: 0.15, g: 0.15, b: 0.15 }, // Gris muy oscuro
          text: { r: 0.6, g: 0.0, b: 0.0 }, // Rojo oscuro
        }
        targetTextScaleRef.current = 1
        break
      case "user":
        targetColorsRef.current = {
          circle: { r: 0.35, g: 0.35, b: 0.35 }, // Gris oscuro (escuchando)
          text: { r: 0.7, g: 0.0, b: 0.0 }, // Rojo más visible
        }
        targetTextScaleRef.current = 0.95
        break
      case "agent":
        targetColorsRef.current = {
          circle: { r: 0.75, g: 0.0, b: 0.0 }, // Rojo intenso (hablando)
          text: { r: 0.85, g: 0.0, b: 0.0 }, // Rojo brillante
        }
        targetTextScaleRef.current = 1.1
        break
    }
  }, [speaker])

  useEffect(() => {
    if (!particlesRef.current || !basePositionsRef.current) return

    const animate = (time: number) => {
      const particles = particlesRef.current
      const basePositions = basePositionsRef.current
      const isTextParticle = isTextParticleRef.current

      if (!particles || !basePositions) {
        frameRef.current = requestAnimationFrame(animate)
        return
      }

      const positions = particles.geometry.attributes.position.array as Float32Array
      const colors = particles.geometry.attributes.color.array as Float32Array
      const t = time * 0.001

      smoothedAudioRef.current += (audioLevel - smoothedAudioRef.current) * 0.06
      const smoothLevel = smoothedAudioRef.current

      textScaleRef.current += (targetTextScaleRef.current - textScaleRef.current) * 0.08

      const lerpSpeed = 0.05
      currentColorsRef.current.circle.r +=
        (targetColorsRef.current.circle.r - currentColorsRef.current.circle.r) * lerpSpeed
      currentColorsRef.current.circle.g +=
        (targetColorsRef.current.circle.g - currentColorsRef.current.circle.g) * lerpSpeed
      currentColorsRef.current.circle.b +=
        (targetColorsRef.current.circle.b - currentColorsRef.current.circle.b) * lerpSpeed
      currentColorsRef.current.text.r += (targetColorsRef.current.text.r - currentColorsRef.current.text.r) * lerpSpeed
      currentColorsRef.current.text.g += (targetColorsRef.current.text.g - currentColorsRef.current.text.g) * lerpSpeed
      currentColorsRef.current.text.b += (targetColorsRef.current.text.b - currentColorsRef.current.text.b) * lerpSpeed

      const maxRadius = 0.765

      for (let i = 0; i < positions.length / 3; i++) {
        const baseX = basePositions[i * 3]
        const baseY = basePositions[i * 3 + 1]
        const isText = isTextParticle[i]

        const dist = Math.sqrt(baseX * baseX + baseY * baseY)
        const angle = Math.atan2(baseY, baseX)

        const breathing = Math.sin(t * 0.8) * 0.02 + Math.sin(t * 1.3) * 0.01
        const audioScale = 1 + smoothLevel * 0.4
        const ripple = Math.sin(dist * 8 - t * 3) * smoothLevel * 0.06
        const swirlAmount = (dist / maxRadius) * smoothLevel * 0.3
        const swirlAngle = angle + Math.sin(t * 2) * swirlAmount

        let newDist = dist * (1 + breathing) * audioScale + ripple
        let newAngle = swirlAngle

        if (isText) {
          const textBreathing = Math.sin(t * 0.8) * 0.015
          const textAudioReact = smoothLevel * 0.2
          newDist = dist * textScaleRef.current * (1 + textBreathing + textAudioReact)
          newAngle = angle + Math.sin(t * 1.5) * smoothLevel * 0.08
        }

        positions[i * 3] = Math.cos(newAngle) * newDist
        positions[i * 3 + 1] = Math.sin(newAngle) * newDist

        if (isText) {
          colors[i * 3] = currentColorsRef.current.text.r
          colors[i * 3 + 1] = currentColorsRef.current.text.g
          colors[i * 3 + 2] = currentColorsRef.current.text.b
        } else {
          const edgeBrightness = (dist / maxRadius) * smoothLevel * 0.15
          colors[i * 3] = Math.min(1, currentColorsRef.current.circle.r + edgeBrightness)
          colors[i * 3 + 1] = Math.min(1, currentColorsRef.current.circle.g + edgeBrightness * 0.3)
          colors[i * 3 + 2] = Math.min(1, currentColorsRef.current.circle.b + edgeBrightness * 0.3)
        }
      }

      particles.geometry.attributes.position.needsUpdate = true
      particles.geometry.attributes.color.needsUpdate = true

      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current)
      }

      frameRef.current = requestAnimationFrame(animate)
    }

    frameRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(frameRef.current)
    }
  }, [audioLevel])

  return <div ref={containerRef} className={`w-[400px] h-[400px] rounded-full overflow-hidden ${className || ""}`} />
}
