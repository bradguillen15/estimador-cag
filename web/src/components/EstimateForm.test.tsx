import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { EstimateForm } from './EstimateForm'

const DESCRIPTION = 'Portal interno para reservar salas de reuniones.'

function setup(busy = false) {
  const onSubmit = vi.fn()
  const user = userEvent.setup()
  render(<EstimateForm busy={busy} onSubmit={onSubmit} />)
  return {
    onSubmit,
    user,
    description: screen.getByLabelText(/descripción del proyecto/i),
    submit: screen.getByRole('button', { name: /generar estimación|generando/i }),
  }
}

describe('EstimateForm', () => {
  it('keeps submit disabled until the description reaches 20 characters', async () => {
    const { user, description, submit } = setup()
    expect(submit).toBeDisabled()

    await user.type(description, 'Muy corto')
    expect(screen.getByText(/9 \/ 2000/)).toBeInTheDocument()
    expect(screen.getByText(/mínimo 20/)).toBeInTheDocument()
    expect(submit).toBeDisabled()

    await user.type(description, ' pero ahora ya alcanza')
    expect(submit).toBeEnabled()
    expect(screen.queryByText(/mínimo 20/)).not.toBeInTheDocument()
  })

  it('ignores surrounding whitespace when counting', async () => {
    const { user, description, submit } = setup()
    await user.type(description, `   ${'x'.repeat(19)}   `)
    expect(submit).toBeDisabled()
  })

  it('submits the trimmed description with the default options', async () => {
    const { user, description, submit, onSubmit } = setup()

    await user.type(description, `  ${DESCRIPTION}  `)
    await user.click(submit)

    expect(onSubmit).toHaveBeenCalledWith({
      description: DESCRIPTION,
      project_type: 'mobile_app',
      detail_level: 'medium',
      output_format: 'phases_table',
    })
  })

  it('submits the options the user picked', async () => {
    const { user, description, submit, onSubmit } = setup()

    await user.type(description, DESCRIPTION)
    await user.selectOptions(screen.getByLabelText('Tipo de proyecto'), 'Pipeline de datos')
    await user.selectOptions(screen.getByLabelText('Nivel de detalle'), 'Detallado')
    await user.selectOptions(screen.getByLabelText('Formato de salida'), 'Narrativo')
    await user.click(submit)

    expect(onSubmit).toHaveBeenCalledWith({
      description: DESCRIPTION,
      project_type: 'data_pipeline',
      detail_level: 'detailed',
      output_format: 'narrative',
    })
  })

  it('submits with Cmd/Ctrl+Enter from the description', async () => {
    const { user, description, onSubmit } = setup()

    await user.type(description, DESCRIPTION)
    await user.keyboard('{Meta>}{Enter}{/Meta}')
    await user.keyboard('{Control>}{Enter}{/Control}')

    expect(onSubmit).toHaveBeenCalledTimes(2)
  })

  it('does not submit an invalid description with the shortcut', async () => {
    const { user, description, onSubmit } = setup()
    await user.type(description, 'corto{Meta>}{Enter}{/Meta}')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows progress and blocks resubmission while busy', async () => {
    const { user, description, submit, onSubmit } = setup(true)

    await user.type(description, `${DESCRIPTION}{Meta>}{Enter}{/Meta}`)

    expect(submit).toHaveTextContent('Generando…')
    expect(submit).toBeDisabled()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
