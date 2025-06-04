import pandas as pd
import numpy as np
import re

def limpiar_datos_entrenamiento():
    """
    Limpia los datos del Excel antes de entrenar
    """
    print("🧹 === LIMPIANDO DATOS DE ENTRENAMIENTO ===")
    
    try:
        # 1. CARGAR ARCHIVO ORIGINAL
        archivo_datos = "data/training/datos_entrenamiento.xlsx"
        archivo_estados = "data/training/estados_conversacion.xlsx"
        
        print(f"📂 Cargando: {archivo_datos}")
        df_datos = pd.read_excel(archivo_datos)
        
        print(f"📂 Cargando: {archivo_estados}")
        df_estados = pd.read_excel(archivo_estados)
        
        # 2. IDENTIFICAR COLUMNAS NUMÉRICAS PROBLEMÁTICAS
        print("\n🔍 Analizando columnas numéricas...")
        
        for df_name, df in [("datos", df_datos), ("estados", df_estados)]:
            print(f"\n📋 Analizando DataFrame: {df_name}")
            print(f"   Columnas: {list(df.columns)}")
            
            for col in df.columns:
                # Detectar columnas que deberían ser numéricas
                if any(keyword in col.lower() for keyword in ['saldo', 'monto', 'valor', 'precio', 'cuota', 'capital', 'interes']):
                    print(f"   🔢 Columna numérica detectada: {col}")
                    
                    # Mostrar valores únicos si hay pocos
                    unique_vals = df[col].dropna().unique()
                    if len(unique_vals) < 10:
                        print(f"      Valores únicos: {unique_vals}")
                    else:
                        print(f"      Primeros valores: {unique_vals[:5]}")
                    
                    # Detectar valores problemáticos
                    problematic = []
                    for val in unique_vals:
                        if pd.notna(val):
                            val_str = str(val)
                            # Buscar formatos problemáticos
                            if (',' in val_str and '.' in val_str) or len(val_str.replace('.', '').replace(',', '')) > 15:
                                problematic.append(val)
                    
                    if problematic:
                        print(f"      ⚠️ Valores problemáticos: {problematic[:3]}")
        
        # 3. FUNCIÓN DE LIMPIEZA NUMÉRICA
        def limpiar_valor_numerico(valor):
            """Convierte valores de texto a float limpiando formatos"""
            if pd.isna(valor):
                return 0.0
            
            valor_str = str(valor).strip()
            
            # Si ya es numérico, devolver tal como está
            if isinstance(valor, (int, float)):
                return float(valor)
            
            # Limpiar texto
            # Remover espacios, símbolos de moneda
            valor_limpio = re.sub(r'[^\d.,-]', '', valor_str)
            
            # Manejar formato colombiano (1.234.567,89)
            if ',' in valor_limpio and '.' in valor_limpio:
                # Formato: 1.234.567,89 -> 1234567.89
                valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
            elif ',' in valor_limpio:
                # Solo coma: 1234567,89 -> 1234567.89
                valor_limpio = valor_limpio.replace(',', '.')
            
            try:
                return float(valor_limpio)
            except:
                print(f"      ❌ No se pudo convertir: {valor} -> usando 0.0")
                return 0.0
        
        # 4. APLICAR LIMPIEZA A AMBOS DATAFRAMES
        for df_name, df in [("datos", df_datos), ("estados", df_estados)]:
            print(f"\n🧹 Limpiando DataFrame: {df_name}")
            
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['saldo', 'monto', 'valor', 'precio', 'cuota', 'capital', 'interes']):
                    print(f"   Limpiando columna: {col}")
                    df[col] = df[col].apply(limpiar_valor_numerico)
        
        # 5. VALIDAR DATOS LIMPIOS
        print("\n✅ Validando datos limpios...")
        
        # Verificar que no hay NaN en columnas críticas
        for df_name, df in [("datos", df_datos), ("estados", df_estados)]:
            print(f"\n📊 Resumen {df_name}:")
            print(f"   Filas: {len(df)}")
            print(f"   Columnas: {len(df.columns)}")
            
            # Contar NaN por columna
            nan_counts = df.isnull().sum()
            if nan_counts.sum() > 0:
                print(f"   ⚠️ Valores faltantes:")
                for col, count in nan_counts[nan_counts > 0].items():
                    print(f"      {col}: {count} NaN")
        
        # 6. GUARDAR ARCHIVOS LIMPIOS
        archivo_datos_limpio = archivo_datos.replace('.xlsx', '_limpio.xlsx')
        archivo_estados_limpio = archivo_estados.replace('.xlsx', '_limpio.xlsx')
        
        df_datos.to_excel(archivo_datos_limpio, index=False)
        df_estados.to_excel(archivo_estados_limpio, index=False)
        
        print(f"\n💾 Archivos guardados:")
        print(f"   📄 {archivo_datos_limpio}")
        print(f"   📄 {archivo_estados_limpio}")
        
        print(f"\n🚀 Ahora ejecuta el entrenamiento con archivos limpios:")
        print(f"python app/machine_learning/train/train_intention_classifier.py --datos {archivo_datos_limpio} --estados {archivo_estados_limpio}")
        
        return archivo_datos_limpio, archivo_estados_limpio
        
    except Exception as e:
        print(f"❌ Error limpiando datos: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    limpiar_datos_entrenamiento()