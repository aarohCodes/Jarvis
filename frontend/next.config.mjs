/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  devIndicators: false, // its bottom-left badge collides with the sidebar's HUD clock
  allowedDevOrigins: ["host.docker.internal"], // lets the Playwright screenshot container load dev JS/HMR assets
};

export default nextConfig;
