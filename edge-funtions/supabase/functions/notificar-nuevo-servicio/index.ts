import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY')
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

const supabase = createClient(SUPABASE_URL!, SUPABASE_SERVICE_ROLE_KEY!)

serve(async (req) => {
  try {
    // 1. Buscamos los correos de los usuarios con ROL 3
    const { data: usuarios, error } = await supabase
      .from('Usuario')
      .select('correo, nombre')
      .eq('rol', 3) // <--- ¡CAMBIO APLICADO! Solo Rol 3
      .not('correo', 'is', null)

    if (error) {
      return new Response("Error DB", { status: 500 })
    }

    if (!usuarios || usuarios.length === 0) {
      return new Response("No hay usuarios con Rol 3 y correo válido", { status: 200 })
    }

    // 2. Preparamos el envío
    const promesasEnvio = usuarios.map((usuario) => {
      if (!usuario.correo) return Promise.resolve()

      return fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${RESEND_API_KEY}`,
        },
        body: JSON.stringify({
          from: 'Soporte Técnico <onboarding@resend.dev>',
          to: usuario.correo,
          subject: `🔔 Nueva Solicitud de Servicio`,
          html: `
            <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; text-align: center;">
              <h2 style="color: #0C4A6E;">¡Hola, ${usuario.nombre}!</h2>
              <p style="font-size: 16px;">Se ha registrado una nueva solicitud de servicio.</p>
              <div style="margin: 30px 0;">
                <p style="background-color: #f3f4f6; padding: 10px; border-radius: 5px;">
                  Revisa la App Administrativa.
                </p>
              </div>
              <p style="color: #666; font-size: 12px;">Gobernación de Aragua</p>
            </div>
          `,
        }),
      })
    })

    await Promise.all(promesasEnvio)

    return new Response(JSON.stringify({ message: "Notificaciones enviadas a Rol 3" }), {
      headers: { "Content-Type": "application/json" },
    })

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 })
  }
})