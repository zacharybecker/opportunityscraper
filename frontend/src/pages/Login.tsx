import { useState } from 'react'
import { Center, Card, TextInput, PasswordInput, Button, Title, Stack, Alert, SegmentedControl, Text, Anchor } from '@mantine/core'
import { useForm } from '@mantine/form'
import { IconAlertCircle } from '@tabler/icons-react'
import { useLogin } from '../hooks/useAuth'
import { Link } from 'react-router-dom'

export default function Login() {
  const loginMutation = useLogin()
  const [authMode, setAuthMode] = useState<string>('email')
  const form = useForm({
    initialValues: { username: '', password: '' },
    validate: {
      username: (v) => (v.length > 0 ? null : authMode === 'ldap' ? 'Username is required' : 'Username or email is required'),
      password: (v) => (v.length > 0 ? null : 'Password is required'),
    },
  })

  return (
    <Center h="100vh" bg="gray.1">
      <Card shadow="md" p="xl" w={400}>
        <Stack>
          <Title order={2} ta="center">OpportunityScraper</Title>

          <SegmentedControl
            value={authMode}
            onChange={setAuthMode}
            data={[
              { label: 'Email / Password', value: 'email' },
              { label: 'LDAP', value: 'ldap' },
            ]}
            fullWidth
          />

          {loginMutation.isError && (
            <Alert icon={<IconAlertCircle size={16} />} color="red" title="Login failed">
              {(loginMutation.error as any)?.response?.data?.detail || 'Invalid credentials'}
            </Alert>
          )}
          <form onSubmit={form.onSubmit((values) => loginMutation.mutate(values))}>
            <Stack>
              <TextInput
                label={authMode === 'ldap' ? 'Username' : 'Username or Email'}
                placeholder={authMode === 'ldap' ? 'Enter LDAP username' : 'Enter username or email'}
                {...form.getInputProps('username')}
              />
              <PasswordInput label="Password" placeholder="Enter password" {...form.getInputProps('password')} />
              <Button type="submit" fullWidth loading={loginMutation.isPending}>
                Login
              </Button>
            </Stack>
          </form>

          {authMode === 'email' && (
            <Stack gap="xs">
              <Text size="sm" ta="center">
                <Anchor component={Link} to="/forgot-password">Forgot password?</Anchor>
              </Text>
              <Text size="sm" ta="center">
                Don't have an account? <Anchor component={Link} to="/register">Register</Anchor>
              </Text>
            </Stack>
          )}
        </Stack>
      </Card>
    </Center>
  )
}
