import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import typescript from '@rollup/plugin-typescript';
import dts from 'rollup-plugin-dts';
import postcss from 'rollup-plugin-postcss';

export default [
  // Main build - CJS & ESM
  {
    input: 'src/index.ts',
    output: [
      {
        file: 'dist/index.js',
        format: 'cjs',
        sourcemap: true,
        exports: 'named',
      },
      {
        file: 'dist/index.esm.js',
        format: 'esm',
        sourcemap: true,
      },
    ],
    plugins: [
      resolve(),
      commonjs(),
      typescript({ tsconfig: './tsconfig.json' }),
      postcss({
        extract: 'styles.css',
        minimize: true,
      }),
    ],
    external: ['react', 'react-dom', 'marked', 'dompurify', 'highlight.js'],
  },
  // UMD build for browser
  {
    input: 'src/index.ts',
    output: {
      file: 'dist/umd/aichat-sdk.min.js',
      format: 'umd',
      name: 'AIChatSDK',
      sourcemap: true,
      globals: {
        react: 'React',
        'react-dom': 'ReactDOM',
      },
    },
    plugins: [
      resolve(),
      commonjs(),
      typescript({ tsconfig: './tsconfig.json' }),
      postcss({
        inject: true,
        minimize: true,
      }),
    ],
    external: ['react', 'react-dom'],
  },
  // Type definitions
  {
    input: 'src/index.ts',
    output: [{ file: 'dist/index.d.ts', format: 'esm' }],
    plugins: [dts()],
    external: [/\.css$/],
  },
];