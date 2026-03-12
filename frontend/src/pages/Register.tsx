import { Center, Card, TextInput, PasswordInput, Button, Title, Stack, Alert, Text, Anchor } from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconAlertCircle } from '@tabler/icons-react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store'
import apiClient from '../api/client'

export default function Register() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const form = useForm({
    initialValues: { username: '', email: '', password: '', confirmPassword: '', display_name: '' },
    validate: {
      username: (v) => (v.length >= 3 ? null : 'Username must be at least 3 characters'),
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : 'Invalid email'),
      password: (v) => (v.length >= 8 ? null : 'Password must be at least 8 characters'),
      confirmPassword: (v, values) => (v === values.password ? null : 'Passwords do not match'),
    },
  })

  const registerMutation = useMutation({
    mutationFn: (values: typeof form.values) =>
      apiClient.post('/auth/register', {
        username: values.username,
        email: values.email,
        password: values.password,
        display_name: values.display_name,
      }).then((r) => r.data),
    onSuccess: (data) => {
      setAuth(data.access_token, data.refresh_token, data.user)
      navigate('/')
    },
  })

  return (
    <Center h="100vh" bg="gray.1">
      <Card shadow="md" p="xl" w={400}>
        <Stack>
          <Title order={2} ta="center">Create Account</Title>
          {registerMutation.isError && (
            <Alert icon={<IconAlertCircle size={16} />} color="red" title="Registration failed">
              {(registerMutation.error as any)?.response?.data?.detail || 'Registration failed'}
            </Alert>
          )}
          <form onSubmit={form.onSubmit((values) => registerMutation.mutate(values))}>
            <Stack>
              <TextInput label="Username" placeholder="Choose a username" {...form.getInputProps('username')} />
              <TextInput label="Email" placeholder="your@email.com" {...form.getInputProps('email')} />
              <TextInput label="Display Name" placeholder="Your Name" {...form.getInputProps('display_name')} />
              <PasswordInput label="Password" placeholder="At least 8 characters" {...form.getInputProps('password')} />
              <PasswordInput label="Confirm Password" placeholder="Repeat password" {...form.getInputProps('confirmPassword')} />
<Button type="submit" fullWidth loading={registerMutation.isPending}>
                Register
              </Button>
            </Stack>
          </form>
          <Text size="sm" ta="center">
            Already have an account? <Anchor component={Link} to="/login">Login</Anchor>
          </Text>
        </Stack>
      </Card>
    </Center>
  )
}
